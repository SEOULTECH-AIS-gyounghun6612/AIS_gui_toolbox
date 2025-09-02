"""OpenGL Renderer Module.

PyOpenGL 기반 3D 지오메트리 렌더링용 고수준 클래스 `OpenGL_Renderer` 제공.

Main Features
-------------
- Open3D 지오메트리(PointCloud, LineSet, TriangleMesh) 렌더링.
- 3D Gaussian Splatting (3DGS) 렌더링 및 실시간 깊이 정렬.
- 데이터 클래스(Resource, Render_Object) 활용.
- 동적 리소스 관리 (추가, 업데이트, 삭제).

"""

from typing import Union, Any
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path

from enum import IntEnum, StrEnum, IntFlag

import numpy as np
from OpenGL.GL import (
    # geometry type
    GL_POINTS, GL_LINES, GL_LINE_STRIP, GL_LINE_LOOP,
    GL_TRIANGLES, GL_TRIANGLE_STRIP, GL_TRIANGLE_FAN,
    # openGL opt
    glEnable,
    GL_DEPTH_TEST, GL_BLEND, GL_CULL_FACE,
    GL_PROGRAM_POINT_SIZE, GL_MULTISAMPLE,
    glBlendFunc, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA,
    # data memory option
    GL_STATIC_DRAW, GL_DYNAMIC_DRAW,
    # about vao, vbo, ebo
    glGenVertexArrays, glGenBuffers,
    glBindVertexArray, glBindBuffer, glBufferData,
    GL_ARRAY_BUFFER, GL_ELEMENT_ARRAY_BUFFER, GL_SHADER_STORAGE_BUFFER,
    glVertexAttribPointer, GL_FALSE, GL_FLOAT,
    glEnableVertexAttribArray,
    glDeleteVertexArrays, glDeleteBuffers,
    # shader
    GL_VERTEX_SHADER, GL_FRAGMENT_SHADER, GL_COMPUTE_SHADER,
    glUseProgram, glGetUniformLocation, glUniform3fv,
    glUniform1f, glUniform1i,
    # render: init background
    glClearColor, glClear,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_STENCIL_BUFFER_BIT,
    # render: compute
    glBindBufferBase, glDispatchCompute, glMemoryBarrier,
    glUniform1ui,
    GL_SHADER_STORAGE_BARRIER_BIT,
    # render: draw
    glDrawElements, glDrawArrays,
    glUniformMatrix4fv, GL_UNSIGNED_INT, glDrawElementsInstanced
    #debug
    # glGetError, GL_NO_ERROR
)

from OpenGL.GL.shaders import ShaderProgram, compileProgram, compileShader

from open3d import geometry

from vision_toolbox.asset import Gaussian_3D
from .scene import View_Cam


O3D_GEOMETRY = Union[
    geometry.PointCloud, geometry.LineSet, geometry.TriangleMesh]


def Build_rnd(shader_type: str) -> ShaderProgram:
    """타입에 맞는 렌더링 셰이더 빌드."""
    _pth = Path(__file__).resolve().parent / "shaders"
    _f_vtx = _pth / f"{shader_type}.vert"
    _f_frg = _pth / f"{shader_type}.frag"
    return compileProgram(
        compileShader(_f_vtx.read_text("UTF-8"), GL_VERTEX_SHADER),
        compileShader(_f_frg.read_text("UTF-8"), GL_FRAGMENT_SHADER),
    )


def Build_compute(key_list: list[str]) -> dict[str, ShaderProgram]:
    """키 리스트에 해당하는 컴퓨트 셰이더 빌드."""
    _pth = Path(__file__).resolve().parent / "shaders"
    return {
        _n: compileProgram(compileShader(
            (_pth / f"{_n}.glsl").read_text("UTF-8"), GL_COMPUTE_SHADER
        )) for _n in key_list
    }


def Create_uniform_setter(shader_prog):
    """
    셰이더 프로그램에 대한 유니폼 세터들을 생성하는 팩토리 함수.
    유니폼 위치를 캐싱하여 성능을 향상시킵니다.
    """
    # 셰이더별로 uniform location을 캐싱
    @lru_cache(maxsize=None)
    def get_loc(name):
        return glGetUniformLocation(shader_prog, name)

    def set_mat4(name, value):
        glUniformMatrix4fv(get_loc(name), 1, GL_FALSE, value)

    def set_vec3(name, value):
        glUniform3fv(get_loc(name), 1, value)

    def set_uint(name, value):
        glUniform1ui(get_loc(name), value)

    def set_int(name, value):
        glUniform1i(get_loc(name), value)

    def set_float(name, value):
        glUniform1f(get_loc(name), value)

    def set_bool(name, value):
        glUniform1i(get_loc(name), int(value))

    return {
        "mat4": set_mat4,
        "vec3": set_vec3,
        "uint": set_uint,
        "int": set_int,
        "float": set_float,
        "bool": set_bool
    }


class Draw_Opt(IntEnum):
    """glBufferData의 드로우 옵션"""
    STATIC = GL_STATIC_DRAW
    DYNAMIC = GL_DYNAMIC_DRAW

class Render_Opt(IntEnum):
    """glEnable/glDisable에 사용되는 렌더링 옵션"""
    DEPTH = GL_DEPTH_TEST                   # 깊이 테스트
    BLEND = GL_BLEND                        # 블렌딩
    FACE_CULL = GL_CULL_FACE                # 면 컬링
    P_ABLE_P_SIZE = GL_PROGRAM_POINT_SIZE   # 프로그래머블 포인트 크기
    MULTISAMPLE_AA = GL_MULTISAMPLE         # 멀티샘플 앤티에일리어싱

class Clear_Opt(IntFlag):
    """glClear에 사용되는 버퍼 비트 마스크"""
    COLOR = GL_COLOR_BUFFER_BIT
    DEPTH = GL_DEPTH_BUFFER_BIT
    STENCIL = GL_STENCIL_BUFFER_BIT

class Prim(IntEnum):
    """glDrawArrays/glDrawElements의 프리미티브 모드"""
    POINTS = GL_POINTS
    LINES = GL_LINES
    LINE_STRIP = GL_LINE_STRIP
    LINE_LOOP = GL_LINE_LOOP
    TRIANGLES = GL_TRIANGLES
    TRIANGLE_STRIP = GL_TRIANGLE_STRIP
    TRIANGLE_FAN = GL_TRIANGLE_FAN

class Buf_Name(IntEnum):
    """glBindBuffer, glBufferData 등의 대상이 되는 버퍼 타입"""
    VBO = GL_ARRAY_BUFFER
    EBO = GL_ELEMENT_ARRAY_BUFFER
    SSBO = GL_SHADER_STORAGE_BUFFER

class Shader_Type(StrEnum):
    GAUSSIAN_SPLAT = "3dgs"
    SIMPLE = "simple"

class Obj_Type(StrEnum):
    GAUSSIAN_SPLAT = "3dgs"
    TRAJ = "trajectory"

OBJ_TO_SHADER: dict[Obj_Type, Shader_Type] = dict(
    zip(Obj_Type, Shader_Type))

SHADER_TO_NUM_VBO: dict[Shader_Type, int] = dict(
    zip(Shader_Type, [0, 2]))


@dataclass
class Resource:
    """렌더링 데이터 래퍼 클래스."""
    obj_type: Obj_Type
    data: Any
    pose: np.ndarray = field(
        default_factory=lambda: np.eye(4, dtype=np.float32))
    color_opt: tuple[float, float, float] | None = None
    draw_opt: Draw_Opt = Draw_Opt.STATIC
    num_vbo: int = field(init=False)

    def __post_init__(self):
        _s_type = OBJ_TO_SHADER[self.obj_type]
        self.num_vbo = SHADER_TO_NUM_VBO[_s_type]


@dataclass
class Render_Object:
    """GPU에 할당된 렌더링 가능 객체 표현 데이터 클래스."""
    vao: int
    shader_type: Shader_Type
    prim_mode: Prim
    model_mat: np.ndarray
    vbos: list[int] = field(default_factory=list)
    ebo: int | None = None
    buffers: dict[str, int] = field(default_factory=dict)
    vtx_count: int = 0
    idx_count: int = 0
    inst_count: int = 0

    def Get_ids(self) -> tuple[int, list[int], int | None]:
        return self.vao, self.vbos, self.ebo


DEFAULT_RENDER_OPT = (
    Render_Opt.DEPTH, Render_Opt.BLEND,
    Render_Opt.P_ABLE_P_SIZE, Render_Opt.MULTISAMPLE_AA
)


class OpenGL_Renderer:
    """3D 데이터 렌더링 메인 클래스."""
    def __init__(
        self, bg_color: tuple[float, float, float, float],  # RGBA
        enable_opts: tuple[Render_Opt, ...] = DEFAULT_RENDER_OPT,
        clear_mask: Clear_Opt = Clear_Opt.COLOR | Clear_Opt.DEPTH
    ):
        self.render_block: dict[str, Render_Object] = {}
        self.shader_obj_map: dict[Shader_Type, list[str]] = {
            _type: [] for _type in Shader_Type
        }
        self.shader_progs: dict[str, ShaderProgram] = {}
        self.bg_color = bg_color
        self.enable_opts = enable_opts
        self.clear_mask = clear_mask
        self.quad_vao, self.quad_vbo, self.quad_ebo = 0, 0, 0
        self.quad_idx_count = 0

        self.sh_dim: int = 0
        self.gau_splat_mode: int = 0

    def __Create_quad_mesh(self):
        _vts = np.array([-1,1, 1,1, 1,-1, -1,-1], dtype=np.float32)
        _faces = np.array([0,1,2, 0,2,3], dtype=np.uint32)
        self.quad_idx_count = _faces.size
        self.quad_vao = glGenVertexArrays(1)
        self.quad_vbo, self.quad_ebo = glGenBuffers(2)

        glBindVertexArray(self.quad_vao)
        glBindBuffer(Buf_Name.VBO, self.quad_vbo)
        glBufferData(Buf_Name.VBO, _vts.nbytes, _vts, Draw_Opt.STATIC)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)
        glBindBuffer(Buf_Name.EBO, self.quad_ebo)
        glBufferData(Buf_Name.EBO, _faces.nbytes, _faces, Draw_Opt.STATIC)
        glBindVertexArray(0)

    def initialize(self):
        """렌더러 초기화 (셰이더 컴파일, GL 옵션, Quad 메시 생성)."""
        # 셰이더 빌드
        _render_progs = {s: Build_rnd(s) for s in Shader_Type}
        _compute_progs = Build_compute([
            "depth_calc", "bitonic_sort", "reorder_data"])
        self.shader_progs = {**_render_progs, **_compute_progs}

        for opt in self.enable_opts:
            glEnable(opt)
            if opt is Render_Opt.BLEND:
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # 3DGS용 공유 Quad 메시 생성
        self.__Create_quad_mesh()

    # init data
    def __Get_data_from_o3d(self, res: Resource):
        """Open3D 지오메트리에서 렌더링 데이터 추출."""
        _g, _type, _c_opt = res.data, res.obj_type, res.color_opt
        _pts, _idx, _colors = np.array([]), np.array([]), None

        if isinstance(_g, (geometry.PointCloud, geometry.LineSet)):
            _pts = np.asarray(_g.points, dtype=np.float32)
            # 색상 정보 설정
            if _g.has_colors():
                _colors = np.asarray(_g.colors, dtype=np.float32)

            if isinstance(_g, geometry.PointCloud):
                _m = Prim.POINTS
            else:
                _m = Prim.LINE_STRIP if _type is Obj_Type.TRAJ else Prim.LINES
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

    def __Bind_simple_data(
        self, vao: int, vbos: list[int], ebo: int | None,
        res: Resource
    ):
        """단순 지오메트리 데이터 바인딩."""
        glBindVertexArray(vao)
        _mode, _data, _idx = self.__Get_data_from_o3d(res)
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

    def __Bind_3dgs_data(self, res: Resource) -> Render_Object:
        """3DGS 데이터를 SSBO에 바인딩."""
        _data: Gaussian_3D = res.data
        _num_3dgs = len(_data.points)

        _f_data = _data.Ready_to_display_flat()
        _ssbo_gaus = glGenBuffers(1)
        glBindBuffer(Buf_Name.SSBO, _ssbo_gaus)
        glBufferData(Buf_Name.SSBO, _f_data.nbytes, _f_data, res.draw_opt)

        _ssbo_sort = glGenBuffers(1)
        glBindBuffer(Buf_Name.SSBO, _ssbo_sort)
        glBufferData(Buf_Name.SSBO, _num_3dgs * 8, None, Draw_Opt.DYNAMIC)

        _ssbo_reordered = glGenBuffers(1)
        glBindBuffer(Buf_Name.SSBO, _ssbo_reordered)
        glBufferData(Buf_Name.SSBO, _f_data.nbytes, None, Draw_Opt.DYNAMIC)
        glBindBuffer(Buf_Name.SSBO, 0)

        return Render_Object(
            vao=self.quad_vao,
            shader_type=Shader_Type.GAUSSIAN_SPLAT,
            prim_mode=Prim.TRIANGLES,
            model_mat=res.pose,
            buffers={
                "gaus": _ssbo_gaus,
                "sort": _ssbo_sort,
                "reordered": _ssbo_reordered
            },
            inst_count=_num_3dgs
        )

    def __Bind_geom(self, vao, vbos, ebo, res: Resource) -> Render_Object:
        if res.obj_type is Obj_Type.GAUSSIAN_SPLAT:
            return self.__Bind_3dgs_data(res)
        return self.__Bind_simple_data(vao, vbos, ebo, res)

    def __Prepare_gl_buffers(self, to_add: dict[str, Resource]):
        _n_vao = len(to_add)
        _n_vbo = sum(res.num_vbo for res in to_add.values())
        _vao = glGenVertexArrays(_n_vao)
        _vbos = glGenBuffers(_n_vbo) if _n_vbo > 0 else []
        _ebo = glGenBuffers(_n_vao)
        if _n_vao == 1:
            _vao, _ebo = [_vao], [_ebo]
        _bind_args, _vb_offset = {}, 0
        for i, (name, res) in enumerate(to_add.items()):
            _num_vbo = res.num_vbo
            _vbo_slice = list(_vbos[_vb_offset : _vb_offset + _num_vbo])
            _bind_args[name] = (_vao[i], _vbo_slice, _ebo[i], res)
            _vb_offset += _num_vbo
        return _bind_args

    def Del_geometry(self, names: list[str]):
        """객체 제거 및 GPU 리소스 해제."""
        _r_block, _s_table = self.render_block, self.shader_obj_map

        _l_vao, _l_vbo, _l_ebo = [], [], []
        for name in names:
            _obj = _r_block.pop(name, None)
            if not _obj:
                continue
            _s_table[_obj.shader_type].remove(name)

            _l_vbo.extend(_obj.vbos)
            _l_vbo.extend(_obj.buffers.values())

            if _obj.shader_type is not Shader_Type.GAUSSIAN_SPLAT:
                _l_vao.append(_obj.vao)
            if _obj.ebo:
                _l_ebo.append(_obj.ebo)
        if _l_vao:
            glDeleteVertexArrays(len(_l_vao), _l_vao)
        if _l_vbo:
            glDeleteBuffers(len(_l_vbo), _l_vbo)
        if _l_ebo:
            glDeleteBuffers(len(_l_ebo), _l_ebo)

    def Set_resources(self, res_block: dict[str, Resource]):
        """장면 리소스 설정 (추가, 업데이트, 삭제)."""
        _old_names = set(self.render_block.keys())
        _new_names = set(res_block.keys())
        _to_del = []
        _to_add = {_n: res_block[_n] for _n in (_new_names - _old_names)}
        _bind_args = {}

        _r_block, _s_table = self.render_block, self.shader_obj_map
        for _n in _old_names & _new_names:
            _old_obj, _new_res = _r_block[_n], res_block[_n]
            if _new_res.num_vbo == len(_old_obj.vbos):
                _bind_args[_n] = (*_old_obj.Get_ids(), _new_res)
                _n_shader_type = OBJ_TO_SHADER[_new_res.obj_type]
                if _old_obj.shader_type is not _n_shader_type:
                    _s_table[_old_obj.shader_type].remove(_n)
                    _s_table[_n_shader_type].append(_n)
            else:
                _to_del.append(_n)
                _to_add[_n] = _new_res

        if _to_del:
            self.Del_geometry(_to_del)
        if _to_add:
            _bind_args.update(self.__Prepare_gl_buffers(_to_add))
        if not _bind_args:
            return

        for _n, _args in _bind_args.items():
            _obj = self.__Bind_geom(*_args)
            _r_block[_n] = _obj
            if _n in _to_add:
                _s_table[_obj.shader_type].append(_n)

    # render
    def __Background_init(self):
        glClearColor(*self.bg_color)
        glClear(self.clear_mask)

    def __Render_each_obj(self, obj: Render_Object, setters: dict):
        setters["mat4"]("model", obj.model_mat)

        glBindVertexArray(obj.vao)
        if obj.shader_type is Shader_Type.GAUSSIAN_SPLAT:
            glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["reordered"])
            glDrawElementsInstanced(
                Prim.TRIANGLES, self.quad_idx_count,
                GL_UNSIGNED_INT, None, obj.inst_count
            )
        elif obj.idx_count:
            glDrawElements(obj.prim_mode, obj.idx_count, GL_UNSIGNED_INT, None)
        elif obj.vtx_count:
            glDrawArrays(obj.prim_mode, 0, obj.vtx_count)

    def __Depth_sort_for_3dgs(self, obj: Render_Object, view_mat: np.ndarray):
        """GPU Bitonic Sort로 깊이 정렬 후 인덱스 버퍼 업데이트."""
        _n_gs = obj.inst_count
        if _n_gs == 0:
            return
        _sh_dim = self.sh_dim # 예시: SH Degree 0 (RGB)
        if _sh_dim == 0:
            _total_dim = 14
        else:
            _num_sh_coeffs = (_sh_dim + 1) * (_sh_dim + 1)
            _total_dim = 11 + 3 * _num_sh_coeffs

        _num_groups = (_n_gs + 1023) // 1024

        # Depth Calculation
        _s_depth = self.shader_progs["depth_calc"]
        _d_setters = Create_uniform_setter(_s_depth)
        glUseProgram(_s_depth)
        _d_setters["mat4"]("view", view_mat)
        _d_setters["uint"]("num_elements", _n_gs)
        _d_setters["int"]("total_dim", _total_dim)
        glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["gaus"])
        glBindBufferBase(Buf_Name.SSBO, 1, obj.buffers["sort"])
        glDispatchCompute(_num_groups, 1, 1)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        _s_sort = self.shader_progs["bitonic_sort"]
        _s_setters = Create_uniform_setter(_s_sort)
        # Bitonic Sort
        glUseProgram(_s_sort)
        glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["sort"])
        _n_stages = (_n_gs - 1).bit_length()
        for _stage in range(_n_stages):
            _s_setters["uint"]("stage", _stage)
            for _sub_stage in range(_stage, -1, -1):
                _s_setters["uint"]("sub_stage", _sub_stage)
                glDispatchCompute(_num_groups, 1, 1)
                glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        _s_reorder = self.shader_progs["reorder_data"]
        _r_setters = Create_uniform_setter(_s_reorder)
        glUseProgram(_s_reorder)
        _r_setters["uint"]("num_elements", _n_gs)
        _r_setters["int"]("total_dim", _total_dim)
        # 셰이더의 binding에 맞춰 버퍼 연결
        glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["sort"])
        glBindBufferBase(Buf_Name.SSBO, 1, obj.buffers["gaus"])
        glBindBufferBase(Buf_Name.SSBO, 2, obj.buffers["reordered"])
        glDispatchCompute(_num_groups, 1, 1)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)


    def Render(self, camera: View_Cam):
        """장면의 모든 객체 렌더링 (유니폼 설정 일반화)."""
        self.__Background_init()
        _r_block = self.render_block

        # 1. Compute Pass: 3DGS 깊이 정렬
        _gs_names = self.shader_obj_map[Shader_Type.GAUSSIAN_SPLAT]
        for _n in _gs_names:
            self.__Depth_sort_for_3dgs(_r_block[_n], camera.view_mat)

        # 2. Render Pass: 모든 객체 렌더링
        for _s_type, _n_list in self.shader_obj_map.items():
            if not _n_list:
                continue

            _shader = self.shader_progs[_s_type]
            glUseProgram(_shader)
            _setters = Create_uniform_setter(_shader)
            _setters["mat4"]("view", camera.view_mat)
            _setters["mat4"]("projection", camera.proj_matrix)

            if _s_type is Shader_Type.GAUSSIAN_SPLAT:
                _setters["vec3"]("cam_pos", camera.position)
                _setters["vec3"]("hfovxy_focal", camera.Get_hfovxy_focal())
                _setters["int"]("sh_dim", self.sh_dim)
                _setters["int"]("render_mod", self.gau_splat_mode)
                _setters["float"]("scale_modifier", 1.0)
                _setters["bool"]("use_stabilization", False)

            # 객체 드로우 콜
            for _n in _n_list:
                self.__Render_each_obj(_r_block[_n], _setters)

        glBindVertexArray(0)
