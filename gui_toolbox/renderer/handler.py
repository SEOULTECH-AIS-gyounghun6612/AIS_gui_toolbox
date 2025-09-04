"""
렌더링 객체 타입별 데이터 처리 및 그리기를 담당하는 핸들러와
다양한 백엔드를 지원하는 소터 네임스페이스를 제공합니다.
"""

from abc import ABC, abstractmethod
from typing import Callable
import numpy as np

from OpenGL.GL import (
    glGenBuffers,
    glBindVertexArray, glBindBuffer, glBufferData,
    glVertexAttribPointer, GL_FALSE, GL_FLOAT,
    glEnableVertexAttribArray,
    glDeleteVertexArrays, glDeleteBuffers,
    glUseProgram, glBindBufferBase, glDispatchCompute, glMemoryBarrier,
    GL_SHADER_STORAGE_BARRIER_BIT,
    glDrawElements, glDrawArrays, glDrawElementsInstanced,
    GL_UNSIGNED_INT
)
from OpenGL.GL.shaders import ShaderProgram

from open3d import geometry
from vision_toolbox.asset import Gaussian_3DGS, Point_Cloud

from .definitions import (
    Resource, Render_Object,
    Buf_Name, Prim, Shader_Type, Draw_Opt, Obj_Type, Sorter_Type,
    Create_splat_buffer
)

# PyTorch 가용성 확인
try:
    import torch
    TORCH_AVAILABLE = torch.cuda.is_available()
except ImportError:
    TORCH_AVAILABLE = False


class Sorter:
    """
    다양한 백엔드를 사용하여 3D 가우시안을 정렬하는 기능을 제공하는 네임스페이스.
    """
    class Base(ABC):
        @abstractmethod
        def Sort(
            self, obj: Render_Object, view_mat: np.ndarray
        ):
            """GPU 데이터를 깊이 순으로 정렬 및 재배열합니다."""
            pass

    class OpenGL(Base):
        """Compute Shader를 이용한 3DGS 깊이 정렬 전문 클래스."""
        def __init__(
            self,
            sh_depth: ShaderProgram,
            sh_sort: ShaderProgram,
            sh_reorder: ShaderProgram,
            setters: dict[str, Callable]
        ):
            self.sh_progs = {
                "depth_calc": sh_depth,
                "bitonic_sort": sh_sort,
                "reorder_data": sh_reorder
            }
            self.setters = setters

        def Sort(
            self, obj: Render_Object, view_mat: np.ndarray
        ):
            """GPU Bitonic Sort로 깊이 정렬 수행."""
            _n_gs = obj.inst_count
            if _n_gs == 0:
                return

            _num_groups = (_n_gs + 1023) // 1024

            # 1. Depth Calculation
            _s_depth = self.sh_progs["depth_calc"]
            _d_setters = self.setters["depth_calc"]
            glUseProgram(_s_depth)
            _d_setters["mat4"]("view", view_mat)
            _d_setters["uint"]("num_elements", _n_gs)
            glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["gaus"])
            glBindBufferBase(Buf_Name.SSBO, 1, obj.buffers["sort"])
            glDispatchCompute(_num_groups, 1, 1)
            glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

            # 2. Bitonic Sort
            _s_sort = self.sh_progs["bitonic_sort"]
            _s_setters = self.setters["bitonic_sort"]
            glUseProgram(_s_sort)
            glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["sort"])
            _n_stages = (_n_gs - 1).bit_length()
            for _stage in range(_n_stages):
                _s_setters["uint"]("stage", _stage)
                for _sub_stage in range(_stage, -1, -1):
                    _s_setters["uint"]("sub_stage", _sub_stage)
                    glDispatchCompute(_num_groups, 1, 1)
                    glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

            # 3. Reorder Data
            _s_reorder = self.sh_progs["reorder_data"]
            _r_setters = self.setters["reorder_data"]
            glUseProgram(_s_reorder)
            _r_setters["uint"]("num_elements", _n_gs)
            glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["sort"])
            glBindBufferBase(Buf_Name.SSBO, 1, obj.buffers["gaus"])
            glBindBufferBase(Buf_Name.SSBO, 2, obj.buffers["reordered"])
            glDispatchCompute(_num_groups, 1, 1)
            glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

    class _Sorter_Helper(Base):
        """Torch/CPU 소터의 공통 GPU 재배열 로직을 담당하는 헬퍼 클래스."""
        def __init__(
            self, sh_reorder: ShaderProgram, setters: dict[str, Callable]
        ):
            self.sh_reorder = sh_reorder
            self.setters = setters

        def _Reorder_data_on_gpu(
            self, obj: Render_Object, indices: np.ndarray
        ):
            """계산된 인덱스를 사용하여 GPU에서 데이터를 재배열합니다."""
            glBindBuffer(Buf_Name.SSBO, obj.buffers["indices"])
            glBufferData(
                Buf_Name.SSBO, indices.nbytes, indices, Draw_Opt.DYNAMIC)

            glUseProgram(self.sh_reorder)
            self.setters["uint"]("num_elements", obj.inst_count)

            glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["indices"])
            glBindBufferBase(Buf_Name.SSBO, 1, obj.buffers["gaus"])
            glBindBufferBase(Buf_Name.SSBO, 2, obj.buffers["reordered"])
            _num_groups = (obj.inst_count + 1023) // 1024
            glDispatchCompute(_num_groups, 1, 1)
            glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

    class Torch(_Sorter_Helper):
        """PyTorch(CUDA)를 사용하여 가우시안을 정렬하는 클래스."""
        def __init__(
            self, sh_reorder: ShaderProgram, setters: dict[str, Callable]
        ):
            if not TORCH_AVAILABLE:
                raise RuntimeError("PyTorch with CUDA is not available.")
            super().__init__(sh_reorder, setters)
            self.gaus_id = None
            self.xyz_buffer = None

        def Sort(
            self, obj: Render_Object, view_mat: np.ndarray
        ):
            """PyTorch로 인덱스를 계산하고 GPU에서 데이터를 재배열합니다."""
            _xyz = obj.cpu_data["xyz"]
            if self.gaus_id != id(obj):
                self.xyz_buffer = torch.tensor(
                    _xyz, device='cuda', dtype=torch.float32)
                self.gaus_id = id(obj)

            _view_mat_torch = torch.tensor(
                view_mat, device='cuda', dtype=torch.float32)
            _xyz_view = self.xyz_buffer @ _view_mat_torch[:3, :3].T + _view_mat_torch[:3, 3]
            _indices = torch.argsort(_xyz_view[:, 2])
            _indices_np = _indices.cpu().numpy().astype(np.uint32)
            self._Reorder_data_on_gpu(obj, _indices_np)

    class CPU(_Sorter_Helper):
        """NumPy(CPU)를 사용하여 가우시안을 정렬하는 클래스."""
        def Sort(
            self, obj: Render_Object, view_mat: np.ndarray
        ):
            """NumPy로 인덱스를 계산하고 GPU에서 데이터를 재배열합니다."""
            _xyz = obj.cpu_data["xyz"]
            _xyz_view = _xyz @ view_mat[:3, :3].T + view_mat[:3, 3]
            _indices = np.argsort(_xyz_view[:, 2]).astype(np.uint32)
            self._Reorder_data_on_gpu(obj, _indices)


class Handler:
    """
    다양한 렌더링 객체의 데이터 처리 및 그리기를 담당하는 핸들러 네임스페이스.
    """
    class Base(ABC):
        """오브젝트 핸들러의 공통 인터페이스 역할을 하는 추상 기본 클래스."""
        @abstractmethod
        def Bind(
            self, vao: int, vbos: list[int], ebo: int | None, res: Resource
        ) -> Render_Object:
            """리소스로부터 데이터를 GPU 버퍼에 바인딩하고 Render_Object 생성."""
            pass

        @abstractmethod
        def Draw(self, obj: Render_Object, quad_idx_count: int):
            """Render_Object를 화면에 그림."""
            pass

        @abstractmethod
        def Release(self, obj: Render_Object):
            """Render_Object가 사용하던 GPU 리소스 해제."""
            pass

    class Simple(Base):
        """단순 지오메트리(o3d) 처리 담당."""
        def _Get_data_from_o3d(self, res: Resource):
            _g, _type, _c_opt = res.data, res.obj_type, res.color_opt
            _pts, _idx, _colors = np.array([]), np.array([]), None
            _m = Prim.POINTS

            if isinstance(_g, Point_Cloud):
                _pts = _g.points.astype(np.float32)
                if hasattr(_g, 'colors') and _g.colors.size > 0:
                    _colors = _g.colors.astype(np.float32) / 255.0
            elif isinstance(_g, (geometry.PointCloud, geometry.LineSet)):
                _pts = np.asarray(_g.points, dtype=np.float32)
                if _g.has_colors():
                    _colors = np.asarray(_g.colors, dtype=np.float32)
                if isinstance(_g, geometry.PointCloud):
                    _m = Prim.POINTS
                else:  # LineSet
                    _m = Prim.LINES
                    if _g.has_lines():
                        _idx = np.asarray(_g.lines).flatten()
            elif isinstance(_g, geometry.TriangleMesh):
                _m = Prim.TRIANGLES
                _pts = np.asarray(_g.vertices, dtype=np.float32)
                if _g.has_vertex_colors():
                    _colors = np.asarray(_g.vertex_colors)
                if _g.has_triangles():
                    _idx = np.asarray(_g.triangles).flatten()
            else:
                raise TypeError(f"지원하지 않는 타입: {type(_g)}")

            if _c_opt:
                _c = np.tile(np.array(_c_opt, "f4"), (len(_pts), 1))
            elif _colors is not None:
                _c = _colors
            else:
                _c = np.full_like(_pts, 0.8, "f4")
            return _m, (_pts, _c), _idx.astype(np.uint32)

        def Bind(
            self, vao: int, vbos: list[int], ebo: int | None, res: Resource
        ) -> Render_Object:
            glBindVertexArray(vao)
            _mode, _data, _idx = self._Get_data_from_o3d(res)
            _v_ct, _i_ct = len(_data[0]), len(_idx)

            for i, d in enumerate(_data):
                glBindBuffer(Buf_Name.VBO, vbos[i])
                glBufferData(Buf_Name.VBO, d.nbytes, d, res.draw_opt)
                glVertexAttribPointer(i, 3, GL_FLOAT, GL_FALSE, 0, None)
                glEnableVertexAttribArray(i)

            if _i_ct > 0:
                _v_ct = 0
                glBindBuffer(Buf_Name.EBO, ebo)
                glBufferData(Buf_Name.EBO, _idx.nbytes, _idx, res.draw_opt)

            glBindVertexArray(0)
            return Render_Object(
                vao, Shader_Type.SIMPLE, _mode, res.pose, vbos, ebo,
                vtx_count=_v_ct, idx_count=_i_ct
            )

        def Draw(self, obj: Render_Object, quad_idx_count: int):
            glBindVertexArray(obj.vao)
            if obj.idx_count:
                glDrawElements(obj.prim_mode, obj.idx_count, GL_UNSIGNED_INT, None)
            elif obj.vtx_count:
                glDrawArrays(obj.prim_mode, 0, obj.vtx_count)

        def Release(self, obj: Render_Object):
            if obj.vao:
                glDeleteVertexArrays(1, [obj.vao])
            if obj.vbos:
                glDeleteBuffers(len(obj.vbos), obj.vbos)
            if obj.ebo:
                glDeleteBuffers(1, [obj.ebo])

    class Gaussian_Splat(Base):
        """3DGS 데이터 처리 담당."""
        def __init__(self, quad_vao: int, sorter_type: Sorter_Type):
            self.quad_vao = quad_vao
            self.sorter_type = sorter_type

        def Bind(
            self, vao: int, vbos: list[int], ebo: int | None, res: Resource
        ) -> Render_Object:
            _data: Gaussian_3DGS = res.data
            _num_3dgs = len(_data.points)

            # Create padded buffer for std430 layout
            _buffer = Create_splat_buffer(_data)

            _ssbo_gaus = glGenBuffers(1)
            glBindBuffer(Buf_Name.SSBO, _ssbo_gaus)
            glBufferData(Buf_Name.SSBO, _buffer.nbytes, _buffer, res.draw_opt)

            _ssbo_reordered = glGenBuffers(1)
            glBindBuffer(Buf_Name.SSBO, _ssbo_reordered)
            glBufferData(Buf_Name.SSBO, _buffer.nbytes, None, Draw_Opt.DYNAMIC)

            _buffers = {"gaus": _ssbo_gaus, "reordered": _ssbo_reordered}
            _cpu_data = None

            if self.sorter_type is Sorter_Type.OPENGL:
                _ssbo_sort = glGenBuffers(1)
                glBindBuffer(Buf_Name.SSBO, _ssbo_sort)
                glBufferData(Buf_Name.SSBO, _num_3dgs * 8, None, Draw_Opt.DYNAMIC)
                _buffers["sort"] = _ssbo_sort
            else:
                _ssbo_indices = glGenBuffers(1)
                glBindBuffer(Buf_Name.SSBO, _ssbo_indices)
                glBufferData(Buf_Name.SSBO, _num_3dgs * 4, None, Draw_Opt.DYNAMIC)
                _buffers["indices"] = _ssbo_indices
                _cpu_data = {"xyz": _data.points}

            glBindBuffer(Buf_Name.SSBO, 0)

            return Render_Object(
                vao=self.quad_vao,
                shader_type=Shader_Type.GAUSSIAN_SPLAT,
                prim_mode=Prim.TRIANGLES,
                model_mat=res.pose,
                buffers=_buffers,
                cpu_data=_cpu_data,
                inst_count=_num_3dgs
            )

        def Draw(self, obj: Render_Object, quad_idx_count: int):
            glBindVertexArray(obj.vao)
            glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["reordered"])
            glDrawElementsInstanced(
                Prim.TRIANGLES, quad_idx_count,
                GL_UNSIGNED_INT, None, obj.inst_count
            )

        def Release(self, obj: Render_Object):
            _buffers = list(obj.buffers.values())
            if _buffers:
                glDeleteBuffers(len(_buffers), _buffers)
