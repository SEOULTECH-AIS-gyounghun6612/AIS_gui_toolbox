"""OpenGL Renderer Module."""

import numpy as np
from OpenGL.GL import (
    glEnable, glBlendFunc, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA,
    glGenVertexArrays, glGenBuffers,
    glBindVertexArray, glBindBuffer, glBufferData,
    glVertexAttribPointer, GL_FALSE, GL_FLOAT,
    glEnableVertexAttribArray,
    glUseProgram,
    glClearColor, glClear,
)
from OpenGL.GL.shaders import ShaderProgram

from .definitions import (
    Resource, Render_Object, Render_Opt, Clear_Opt,
    Shader_Type, Buf_Name, Draw_Opt, Sorter_Type,
    Build_rnd, Build_compute, Create_uniform_setter,
    OBJ_TO_SHADER, DEFAULT_RENDER_OPT
)
from .scene_manager import View_Cam
from .handler import Sorter, Handler


class OpenGL_Renderer:
    """3D 데이터 렌더링 메인 클래스 (관리자 역할)."""
    def __init__(
        self,
        bg_color: tuple[float, float, float, float],  # RGBA
        sorter_type: Sorter_Type = Sorter_Type.OPENGL,
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

        self.sh_dim: int = 0
        self.gau_splat_mode: int = 0

        self.sorter_type = sorter_type
        self.sorter: Sorter.Base | None = None
        self.handlers: dict[Shader_Type, Handler.Base] = {}

    def _Create_quad_mesh(self):
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

    def Initialize(self):
        """렌더러 초기화 (셰이더, GL 옵션, 핸들러 생성)."""
        _render_progs = {s.value: Build_rnd(s) for s in Shader_Type}
        _compute_progs = Build_compute([
            "depth_calc", "bitonic_sort", "reorder_data",
            "reorder_data_from_indices"
        ])
        self.shader_progs = {**_render_progs, **_compute_progs}
        self.setters = {
            _n: Create_uniform_setter(p) for _n, p in self.shader_progs.items()
        }

        for opt in self.enable_opts:
            glEnable(opt)
            if opt is Render_Opt.BLEND:
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self._Create_quad_mesh()

        if self.sorter_type is Sorter_Type.OPENGL:
            self.sorter = Sorter.OpenGL(
                _compute_progs["depth_calc"],
                _compute_progs["bitonic_sort"],
                _compute_progs["reorder_data"],
                {
                    "depth_calc": self.setters["depth_calc"],
                    "bitonic_sort": self.setters["bitonic_sort"],
                    "reorder_data": self.setters["reorder_data"]
                }
            )
        elif self.sorter_type is Sorter_Type.TORCH:
            self.sorter = Sorter.Torch(
                _compute_progs["reorder_data_from_indices"],
                self.setters["reorder_data_from_indices"]
            )
        else:
            self.sorter = Sorter.CPU(
                _compute_progs["reorder_data_from_indices"],
                self.setters["reorder_data_from_indices"]
            )

        self.handlers = {
            Shader_Type.SIMPLE: Handler.Simple(),
            Shader_Type.GAUSSIAN_SPLAT: Handler.Gaussian_Splat(
                self.quad_vao, self.sorter_type)
        }

    def _Bind_geom(self, vao, vbos, ebo, res: Resource) -> Render_Object:
        _shader_type = OBJ_TO_SHADER[res.obj_type]
        _handler = self.handlers[_shader_type]
        return _handler.Bind(vao, vbos, ebo, res)

    def _Prepare_gl_buffers(self, resources: dict[str, Resource]):
        _n_res = len(resources)
        _n_vbo = sum(res.num_vbo for res in resources.values())
        _vao = glGenVertexArrays(_n_res) if _n_res > 0 else []
        _vbos = glGenBuffers(_n_vbo) if _n_vbo > 0 else []
        _ebo = glGenBuffers(_n_res) if _n_res > 0 else []
        if _n_res == 1:
            _vao, _ebo = [_vao], [_ebo]
        
        _bind_args, _vb_offset = {}, 0
        for i, (name, res) in enumerate(resources.items()):
            _num_vbo = res.num_vbo
            _vbo_slice = list(_vbos[_vb_offset : _vb_offset + _num_vbo])
            _bind_args[name] = (_vao[i], _vbo_slice, _ebo[i], res)
            _vb_offset += _num_vbo
        return _bind_args

    def Remove_resources(self, names: list[str]):
        """이름에 해당하는 리소스들을 렌더링 목록에서 제거합니다."""
        for name in names:
            _obj = self.render_objects.pop(name, None)
            if not _obj:
                continue
            self.shader_obj_map[_obj.shader_type].remove(name)
            self.handlers[_obj.shader_type].Release(_obj)

    def Add_or_update_resources(self, resources: dict[str, Resource]):
        """리소스들을 렌더링 목록에 추가하거나 업데이트합니다."""
        # 기존 리소스가 있다면 먼저 제거
        self.Remove_resources(list(resources.keys()))

        # 새 리소스 준비 및 바인딩
        _bind_args = self._Prepare_gl_buffers(resources)
        for name, args in _bind_args.items():
            _obj = self._Bind_geom(*args)
            self.render_objects[name] = _obj
            self.shader_obj_map[_obj.shader_type].append(name)

    def _Background_init(self):
        glClearColor(*self.bg_color)
        glClear(self.clear_mask)

    def _Render_each_obj(self, obj: Render_Object, setters: dict):
        setters["mat4"]("model", obj.model_mat)
        self.handlers[obj.shader_type].Draw(obj, self.quad_idx_count)

    def _Sort_and_reorder_gaussians(self, obj: Render_Object, camera: View_Cam):
        self.sorter.Sort(obj, camera.view_mat)

    def Render(self, camera: View_Cam):
        self._Background_init()
        _r_objs = self.render_objects

        _gs_names = self.shader_obj_map[Shader_Type.GAUSSIAN_SPLAT]
        for _n in _gs_names:
            self._Sort_and_reorder_gaussians(_r_objs[_n], camera)

        for _s_type, _n_list in self.shader_obj_map.items():
            if not _n_list:
                continue

            _s_name = _s_type.value
            _shader = self.shader_progs[_s_name]
            glUseProgram(_shader)
            _setters = self.setters[_s_name]
            _setters["mat4"]("view", camera.view_mat)
            _setters["mat4"]("projection", camera.proj_mat)

            if _s_type is Shader_Type.GAUSSIAN_SPLAT:
                _cam_data = camera.cam_data
                _fx = _cam_data.intrinsics[0, 0]
                _fy = _cam_data.intrinsics[1, 1]
                _w, _h = _cam_data.image_size
                _setters["vec2"]("focal", np.array([_fx, _fy]))
                _setters["vec2"]("viewport", np.array([_w, _h]))
                _setters["vec3"]("cam_pos", _cam_data.pose[:3, 3])
                _setters["int"]("sh_dim", self.sh_dim)
                _setters["int"]("render_mod", self.gau_splat_mode)
                _setters["float"]("scale_modifier", 1.0)
                _setters["bool"]("use_stabilization", False)

            for _n in _n_list:
                self._Render_each_obj(_r_objs[_n], _setters)

        glBindVertexArray(0)