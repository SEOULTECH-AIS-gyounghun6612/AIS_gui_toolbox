"OpenGL Renderer Module."

import numpy as np
from OpenGL.GL import (
    glEnable, glBlendFunc, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA,
    glGenVertexArrays, glGenBuffers, glDeleteVertexArrays, glDeleteBuffers,
    glBindVertexArray, glBindBuffer, glBufferData,
    glVertexAttribPointer, GL_FALSE, GL_FLOAT, GL_UNSIGNED_INT,
    glEnableVertexAttribArray,
    glUseProgram, glBindBufferBase, glDispatchCompute, glMemoryBarrier,
    GL_SHADER_STORAGE_BARRIER_BIT,
    glClearColor, glClear, glDrawElements, glDrawArrays, glDrawElementsInstanced,
    glGetString, GL_VERSION, GL_VENDOR, GL_RENDERER, glGetError, GL_NO_ERROR
)
from OpenGL.GL.shaders import ShaderProgram
from OpenGL.error import GLError

from open3d import geometry
from vision_toolbox.asset import Gaussian_3DGS, Point_Cloud

from .definitions import (
    Resource, Render_Object, Render_Opt, Clear_Opt,
    Shader_Type, Buf_Name, Draw_Opt, Prim,
    Build_rnd, Build_compute, Create_uniform_setter, Create_splat_buffer,
    OBJ_TO_SHADER, DEFAULT_RENDER_OPT
)
from .view_camera import View_Cam


class OpenGL_Renderer:
    """3D 데이터 렌더링, 버퍼 관리, 정렬 등 모든 OpenGL 작업을 처리하는 메인 클래스."""
    def __init__(
        self,
        bg_color: tuple[float, float, float, float],  # RGBA
        enable_opts: tuple[Render_Opt, ...] = DEFAULT_RENDER_OPT,
        clear_mask: Clear_Opt = Clear_Opt.COLOR | Clear_Opt.DEPTH
    ):
        self.render_objects: dict[str, Render_Object] = {}
        self.shader_obj_map: dict[Shader_Type, list[str]] = {
            _type: [] for _type in Shader_Type
        }
        self.shader_progs: dict[str, ShaderProgram] = {}
        self.setters: dict[str, dict] = {}
        self.bg_color = bg_color
        self.enable_opts = enable_opts
        self.clear_mask = clear_mask
        self.quad_vao, self.quad_vbo, self.quad_ebo = 0, 0, 0
        self.quad_idx_count = 0

    def _check_gl_error(self, context_message: str = ""):
        error = glGetError()
        if error != GL_NO_ERROR:
            try:
                error_string = GLError.err_string(error)
            except Exception:
                error_string = f"Unknown error code: {error}"
            print(f"OpenGL Error ({context_message}): {error_string}")

    def _create_quad_mesh(self):
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
        self._check_gl_error("Create Quad Mesh")

    def Initialize(self):
        """렌더러 초기화 (셰이더, GL 옵션, 핸들러 생성)."""
        print("--- OpenGL Context Info ---")
        print(f"Vendor: {glGetString(GL_VENDOR).decode()}")
        print(f"Renderer: {glGetString(GL_RENDERER).decode()}")
        print(f"OpenGL Version: {glGetString(GL_VERSION).decode()}")
        print("---------------------------")

        _render_progs = {s.value: Build_rnd(s) for s in Shader_Type}
        _compute_progs = Build_compute(["depth_calc", "bitonic_sort", "reorder_data"])
        self.shader_progs = {**_render_progs, **_compute_progs}
        self.setters = {
            _n: Create_uniform_setter(p) for _n, p in self.shader_progs.items()
        }
        self._check_gl_error("Shader Compilation")

        for opt in self.enable_opts:
            glEnable(opt)
            if opt is Render_Opt.BLEND:
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._check_gl_error("GL Options Enable")

        self._create_quad_mesh()
        self._check_gl_error("Renderer Initialization Complete")

    def _bind_simple_geom(self, name: str, vao: int, vbos: list, ebo: int, res: Resource) -> Render_Object:
        print(f"[Renderer DEBUG] Binding Simple Geometry: '{name}'")
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
            raise TypeError(f"Unsupported geometry type: {type(_g)}")

        if _c_opt:
            _c = np.tile(np.array(_c_opt, "f4"), (len(_pts), 1))
        elif _colors is not None:
            _c = _colors
        else:
            _c = np.full_like(_pts, 0.8, "f4")
        
        _data = (_pts, _c)
        _idx = _idx.astype(np.uint32)
        _v_ct, _i_ct = len(_data[0]), len(_idx)
        print(f"  - Type: {_type.value}, Vertices: {_v_ct}, Indices: {_i_ct}")
        print(f"  - Points data (first 3):\n{_pts[:3]}")
        print(f"  - Colors data (first 3):\n{_c[:3]}")
        print(f"  - Indices data (first 6):\n{_idx[:6]}")

        glBindVertexArray(vao)
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
            vao, Shader_Type.SIMPLE, _m, res.pose, vbos, ebo,
            vtx_count=_v_ct, idx_count=_i_ct
        )

    def _bind_gaussian_splat(self, name: str, res: Resource) -> Render_Object:
        print(f"[Renderer DEBUG] Binding Gaussian Splat: '{name}'")
        _data: Gaussian_3DGS = res.data
        _num_3dgs = len(_data.points)
        print(f"  - Gaussians: {_num_3dgs}")

        _buffer = Create_splat_buffer(_data)

        _ssbo_gaus = glGenBuffers(1)
        glBindBuffer(Buf_Name.SSBO, _ssbo_gaus)
        glBufferData(Buf_Name.SSBO, _buffer.nbytes, _buffer, res.draw_opt)

        _ssbo_reordered = glGenBuffers(1)
        glBindBuffer(Buf_Name.SSBO, _ssbo_reordered)
        glBufferData(Buf_Name.SSBO, _buffer.nbytes, None, Draw_Opt.DYNAMIC)

        _ssbo_sort = glGenBuffers(1)
        glBindBuffer(Buf_Name.SSBO, _ssbo_sort)
        glBufferData(Buf_Name.SSBO, _num_3dgs * 8, None, Draw_Opt.DYNAMIC)

        _buffers = {
            "gaus": _ssbo_gaus, 
            "reordered": _ssbo_reordered,
            "sort": _ssbo_sort
        }
        glBindBuffer(Buf_Name.SSBO, 0)

        return Render_Object(
            vao=self.quad_vao,
            shader_type=Shader_Type.GAUSSIAN_SPLAT,
            prim_mode=Prim.TRIANGLES,
            model_mat=res.pose,
            buffers=_buffers,
            inst_count=_num_3dgs
        )

    def _prepare_gl_buffers(self, resources: dict[str, Resource]):
        _n_res = len(resources)
        _n_vbo = sum(res.num_vbo for res in resources.values())
        
        _vao = glGenVertexArrays(_n_res) if _n_res > 0 else []
        _vbos = glGenBuffers(_n_vbo) if _n_vbo > 0 else []
        _ebo = glGenBuffers(_n_res) if _n_res > 0 else []

        _vao = np.atleast_1d(_vao).tolist()
        _vbos = np.atleast_1d(_vbos).tolist()
        _ebo = np.atleast_1d(_ebo).tolist()

        _bind_args, _vb_offset = {}, 0
        for i, (name, res) in enumerate(resources.items()):
            _num_vbo = res.num_vbo
            _vbo_slice = _vbos[_vb_offset : _vb_offset + _num_vbo]
            _bind_args[name] = (_vao[i], _vbo_slice, _ebo[i], res)
            _vb_offset += _num_vbo
        return _bind_args

    def Add_or_update_resources(self, resources: dict[str, Resource]):
        """리소스들을 렌더링 목록에 추가하거나 업데이트합니다."""
        self.Remove_resources(list(resources.keys()))

        _bind_args = self._prepare_gl_buffers(resources)
        for name, (vao, vbos, ebo, res) in _bind_args.items():
            s_type = OBJ_TO_SHADER[res.obj_type]
            if s_type == Shader_Type.SIMPLE:
                _obj = self._bind_simple_geom(name, vao, vbos, ebo, res)
            elif s_type == Shader_Type.GAUSSIAN_SPLAT:
                _obj = self._bind_gaussian_splat(name, res)
            else:
                continue
            
            self.render_objects[name] = _obj
            self.shader_obj_map[_obj.shader_type].append(name)
        self._check_gl_error(f"Add/Update Resource: {list(resources.keys())}")

    def Remove_resources(self, names: list[str]):
        """이름에 해당하는 리소스들을 렌더링 목록에서 제거합니다."""
        for name in names:
            _obj = self.render_objects.pop(name, None)
            if not _obj:
                continue
            
            if _obj.shader_type == Shader_Type.GAUSSIAN_SPLAT:
                _buffers = list(_obj.buffers.values())
                if _buffers:
                    glDeleteBuffers(len(_buffers), _buffers)
            else: # Simple geometry
                if _obj.vao: glDeleteVertexArrays(1, [_obj.vao])
                if _obj.vbos: glDeleteBuffers(len(_obj.vbos), _obj.vbos)
                if _obj.ebo: glDeleteBuffers(1, [_obj.ebo])

            self.shader_obj_map[_obj.shader_type].remove(name)

    def _background_init(self):
        glClearColor(*self.bg_color)
        glClear(self.clear_mask)

    def _sort_gaussians(self, obj: Render_Object, view_mat: np.ndarray):
        """GPU Bitonic Sort로 깊이 정렬 수행."""
        _n_gs = obj.inst_count
        if _n_gs == 0: return

        _num_groups = (_n_gs + 1023) // 1024

        glUseProgram(self.shader_progs["depth_calc"])
        _d_setters = self.setters["depth_calc"]
        _d_setters["mat4"]("view", view_mat)
        _d_setters["uint"]("num_elements", _n_gs)
        glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["gaus"])
        glBindBufferBase(Buf_Name.SSBO, 1, obj.buffers["sort"])
        glDispatchCompute(_num_groups, 1, 1)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        glUseProgram(self.shader_progs["bitonic_sort"])
        _s_setters = self.setters["bitonic_sort"]
        glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["sort"])
        _n_stages = (_n_gs - 1).bit_length()
        for _stage in range(_n_stages):
            _s_setters["uint"]("stage", _stage)
            for _sub_stage in range(_stage, -1, -1):
                _s_setters["uint"]("sub_stage", _sub_stage)
                glDispatchCompute(_num_groups, 1, 1)
                glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        glUseProgram(self.shader_progs["reorder_data"])
        _r_setters = self.setters["reorder_data"]
        _r_setters["uint"]("num_elements", _n_gs)
        glBindBufferBase(Buf_Name.SSBO, 0, obj.buffers["sort"])
        glBindBufferBase(Buf_Name.SSBO, 1, obj.buffers["gaus"])
        glBindBufferBase(Buf_Name.SSBO, 2, obj.buffers["reordered"])
        glDispatchCompute(_num_groups, 1, 1)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

    def Render(self, camera: View_Cam):
        print("[Renderer DEBUG] Render Call") # Check if the render loop is running
        self._background_init()
        _r_objs = self.render_objects

        _gs_names = self.shader_obj_map[Shader_Type.GAUSSIAN_SPLAT]
        for _n in _gs_names:
            self._sort_gaussians(_r_objs[_n], camera.view_mat)
        self._check_gl_error("After Gaussian Sort")

        for _s_type, _n_list in self.shader_obj_map.items():
            if not _n_list: continue

            _s_name = _s_type.value
            glUseProgram(self.shader_progs[_s_name])
            _setters = self.setters[_s_name]

            if _s_type is Shader_Type.GAUSSIAN_SPLAT:
                _setters["mat4"]("projection", camera.proj_mat)
                _setters["mat4"]("view", camera.view_mat)
                _cam_data = camera.cam_data
                _fx, _fy = _cam_data.intrinsics[0, 0], _cam_data.intrinsics[1, 1]
                _w, _h = _cam_data.image_size
                _setters["vec2"]("focal", np.array([_fx, _fy]))
                _setters["vec2"]("viewport", np.array([_w, _h]))
                _setters["vec3"]("cam_pos", _cam_data.pose[:3, 3])
                _setters["int"]("sh_degree", 0) # SH_Degree 0 for now
            else:
                _setters["mat4"]("projection", camera.proj_mat)
                _setters["mat4"]("view", camera.view_mat)
            self._check_gl_error(f"Set Common Uniforms for {_s_name}")

            for _n in _n_list:
                obj = _r_objs[_n]
                _setters["mat4"]("model", obj.model_mat)
                
                if _s_type is Shader_Type.GAUSSIAN_SPLAT:
                    glBindVertexArray(obj.vao)
                    glBindBufferBase(Buf_Name.SSBO, 2, obj.buffers["reordered"])
                    glDrawElementsInstanced(
                        Prim.TRIANGLES, self.quad_idx_count,
                        GL_UNSIGNED_INT, None, obj.inst_count
                    )
                else: # Simple Geometry
                    glBindVertexArray(obj.vao)
                    if obj.idx_count > 0:
                        glDrawElements(obj.prim_mode, obj.idx_count, GL_UNSIGNED_INT, None)
                    elif obj.vtx_count > 0:
                        glDrawArrays(obj.prim_mode, 0, obj.vtx_count)

            self._check_gl_error(f"Draw Call for {_s_name}")

        glBindVertexArray(0)