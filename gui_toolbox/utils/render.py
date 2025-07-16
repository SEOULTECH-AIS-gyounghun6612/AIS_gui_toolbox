from typing import Literal, Union, Any
from dataclasses import dataclass, field
from pathlib import Path

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
    GL_STATIC_DRAW, GL_DYNAMIC_DRAW, GL_STREAM_DRAW,
    # about vao, vbo, ebo
    glGenVertexArrays, glGenBuffers,
    glBindVertexArray, glBindBuffer, glBufferData,
    GL_ARRAY_BUFFER, GL_ELEMENT_ARRAY_BUFFER, GL_SHADER_STORAGE_BUFFER,
    glVertexAttribPointer, GL_FALSE, GL_FLOAT,
    glEnableVertexAttribArray, glVertexAttribDivisor,
    glDeleteVertexArrays, glDeleteBuffers,
    # shader
    GL_VERTEX_SHADER, GL_FRAGMENT_SHADER, GL_COMPUTE_SHADER,
    glUseProgram, glGetUniformLocation, glUniform2f, 
    # render: init background
    glClearColor, glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    # render: compute
    glBindBufferBase, glDispatchCompute, glMemoryBarrier, glUniform1ui,
    GL_SHADER_STORAGE_BARRIER_BIT, GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT,
    # render: draw
    glDrawElements, glDrawArrays, glDrawArraysInstanced,
    glUniformMatrix4fv, GL_UNSIGNED_INT
)

from OpenGL.GL.shaders import ShaderProgram, compileProgram, compileShader

from open3d import geometry

# from .camera import Pose


O3D_GEOMETRY = Union[
    geometry.PointCloud, geometry.LineSet, geometry.TriangleMesh]

class Const():
    Draw_opt = {
        "static": GL_STATIC_DRAW,
        "dynamic": GL_DYNAMIC_DRAW,
        "stream": GL_STREAM_DRAW
    }

    Render_opt = {
        "depth": GL_DEPTH_TEST,         # 깊이 테스트
        "blend": GL_BLEND,              # 깊이 테스트
        "face": GL_CULL_FACE,           # 깊이 테스트
        "pps": GL_PROGRAM_POINT_SIZE,   # 깊이 테스트
        "aa": GL_MULTISAMPLE,           # 깊이 테스트
    }

    Primitive_Mode = {
        "pts": GL_POINTS,
        "lines": GL_LINES,
        "line_strip": GL_LINE_STRIP,
        "line_loop": GL_LINE_LOOP,
        "tris": GL_TRIANGLES,
        "tri_strip": GL_TRIANGLE_STRIP,
        "tri_fan": GL_TRIANGLE_FAN,
    }


@dataclass
class Gaussian_3D():
    pts: np.ndarray
    clrs: np.ndarray
    alphas: np.ndarray
    scales: np.ndarray
    quats: np.ndarray


@dataclass
class Resource():
    info: Literal["3dgs", "trajectory"]

    data: Any
    num_vbo: int  # 3dgs = 12, simple = 2

    color_opt: tuple[float, float, float] | None = None
    draw_opt: Literal["static", "dynamic", "stream"] = "static"


@dataclass
class Render_Object():
    # resource
    va: Any
    vbs: list
    eb: Any

    # shader and render
    shader_name : str
    mode: str
    m_matrix: np.ndarray

    buffer: dict[str, Any] = field(default_factory=dict)

    # additional info
    vertex_count: int = 0       # 배열 기반 렌더링 시 사용할 정점 개수
    index_count: int = 0        # 인덱스 기반 렌더링 시 사용할 인덱스 개수
    instance_count: int = 0     # 인스턴스 렌더링 시 사용할 인스턴스 개수


def Build_render_shader(shader_type: str):
    _pth = Path(__file__).resolve().parent / "shaders"
    _f_vertex = _pth / f"{shader_type}.vert"
    _f_frag = _pth / f"{shader_type}.frag"

    assert _f_vertex.exists() and _f_frag.exists()

    return compileProgram(
        compileShader(_f_vertex.read_text(), GL_VERTEX_SHADER),
        compileShader(_f_frag.read_text(), GL_FRAGMENT_SHADER),
    )

def Build_compute_shader(key_list: list[str]):
    _pth = Path(__file__).resolve().parent / "shaders"

    return dict((
        _n,
        compileProgram(
            compileShader((_pth / f"{_n}.glsl").read_text(), GL_COMPUTE_SHADER)
        )    
    ) for _n in key_list)


class OpenGL_Renderer:
    """Open3D 지오메트리를 받아 OpenGL로 렌더링하는 역할"""
    def __init__(
        self,
        background: tuple[float, float, float, float],
        enable_opt: list[Literal["depth", "blend", "face", "pps", "aa"]]
    ):
        self.render_block: dict[str, Render_Object] = {}  # geometry block
        self.shader_to_name_map: dict[str, list[str]] = {
            "simple": [],
            "3dgs": []
        }
        self.shader_program = {}

        self.background: tuple[float, float, float, float] = background

        self.enable_opt = enable_opt

    def initialize(self):
        # get shader
        _shader_program = dict((
            _n, Build_render_shader(_n)
        ) for _n in ["simple", "3dgs"])

        _shader_program.update(
            Build_compute_shader(["depth_calc", "bitonic_sort", "reorder_data"])
        )
        self.shader_program = _shader_program

        # init OpenGL Update
        _en_opt = self.enable_opt
        for _opt in _en_opt:
            glEnable(Const.Render_opt[_opt])
            if _opt == "blend":
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # data initialize
    def __Get_data_from_o3d__(self, resource: Resource):
        _g: O3D_GEOMETRY = resource.data  # geometry
        _i = resource.info  # info
        _c_opt = resource.color_opt

        _pts = np.array([], dtype=np.float32)
        _idx = np.array([], dtype=np.uint32)
        _colors = None

        if isinstance(_g, (geometry.PointCloud, geometry.LineSet)):
            _pts = np.asarray(_g.points, dtype=np.float32)
            if _g.has_colors():
                _colors = np.asarray(_g.colors, dtype=np.float32)

            if isinstance(_g, geometry.PointCloud):
                _mode = "pts"
            else:  # LineSet
                _mode = "line_strip" if _i == "trajectory" else "lines"
                if _g.has_lines():
                    _idx = np.asarray(_g.lines, dtype=np.uint32).flatten()

        elif isinstance(_g, geometry.TriangleMesh):
            _mode = "tris"
            _pts = np.asarray(_g.vertices, dtype=np.float32)
            if _g.has_vertex_colors():
                _colors = np.asarray(_g.vertex_colors, dtype=np.float32)
            if _g.has_triangles():
                _idx = np.asarray(_g.triangles, dtype=np.uint32).flatten()

        else:
            raise ValueError(f"지원하지 않는 지오메트리 타입: {type(_g)}")

        if _c_opt is not None:
            # 1순위: color_opt가 지정된 경우
            _c = np.tile(np.array(_c_opt, dtype=np.float32), (len(_pts), 1))
        elif _colors is not None:
            # 2순위: 지오메트리에 자체 색상이 있는 경우
            _c = _colors
        else:
            # 3순위: 색상 정보가 전혀 없으면 기본 회색으로 설정
            _c = np.ones_like(_pts, dtype=np.float32) * 0.8

        return _mode, (_pts, _c), _idx

    def __Bind_simple_data__(self, va, vbs, eb, resource: Resource, draw_opt):
        """단순 지오메트리 데이터의 바인딩 및 VAO 설정을 처리합니다."""
        glBindVertexArray(va)

        _shader = "simple"
        _mode, _data, _idx = self.__Get_data_from_o3d__(resource)

        _ct_list =  [len(_data[0]), 0, 0] # vert_count, idx_count, inst_count

        for _ct, _d in enumerate(_data):  # VBOs: 0=points, 1=colors
            glBindBuffer(GL_ARRAY_BUFFER, vbs[_ct])
            glBufferData(GL_ARRAY_BUFFER, _d.nbytes, _d, draw_opt)
            glVertexAttribPointer(_ct, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(_ct)

        # EBO 업데이트
        index_count = len(_idx)
        if index_count > 0:
            _ct_list[0] = 0
            _ct_list[1] = index_count
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, eb)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, _idx.nbytes, _idx, draw_opt)

        glBindVertexArray(0)
        _matrix = np.eye(4)

        return Render_Object(
            va, vbs, eb, _shader, _mode, _matrix, {}, *_ct_list
        )

    def __Bind_3dgs_data__(self, va, vbs, eb, resource: Resource, draw_opt):
        """3DGS 데이터의 바인딩 및 VAO 설정을 처리합니다."""
        glBindVertexArray(va)

        _shader = "3dgs"
        _mode = "tri_strip"
        _size = {"pts": 3, "clrs": 3, "alphas": 1, "scales": 3, "quats": 4}
        _data: Gaussian_3D = resource.data
        _num_3dgs = len(_data.pts)
        _ct_list = [0, 0, _num_3dgs] # vert, idx, inst

        for _ct, (_k, _s) in enumerate(_size.items()):
            _d: np.ndarray = getattr(_data, _k)

            _ct_a = 2 * _ct

            glBindBuffer(GL_ARRAY_BUFFER, vbs[_ct_a])
            glBufferData(GL_ARRAY_BUFFER, _d.nbytes, _d, draw_opt)
            glVertexAttribPointer(_ct_a, _s, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(_ct_a)
            glVertexAttribDivisor(_ct_a, 1)

            _ct_b = (2 * _ct) + 1

            glBindBuffer(GL_ARRAY_BUFFER, vbs[_ct_b])
            glBufferData(GL_ARRAY_BUFFER, _d.nbytes, _d, draw_opt)
            glVertexAttribPointer(_ct_b, _s, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(_ct_b)
            glVertexAttribDivisor(_ct_b, 1)

        _b_size = _num_3dgs * 8
        for _ct in range(2):
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, vbs[10 + _ct])
            glBufferData(
                GL_SHADER_STORAGE_BUFFER, _b_size, None, GL_DYNAMIC_DRAW)

        glBindVertexArray(0)

        _matrix = np.eye(4)

        return Render_Object(
            va, vbs[:-2], eb,
            _shader, _mode, _matrix,
            {"ssbos": vbs[-2:]},
            *_ct_list
        )

    def __Bind_geom__(self, va, vbs: list, eb, resource: Resource):
        _draw_opt = Const.Draw_opt[resource.draw_opt]

        if resource.info == "gs_3d":
            _binder = self.__Bind_3dgs_data__
        else:  # simple
            _binder = self.__Bind_simple_data__

        return _binder(va, vbs, eb, resource, _draw_opt)

    def Set_resources(self, res_block: dict[str, Resource]):
        _r_block = self.render_block
        _s_table = self.shader_to_name_map

        _add = dict((
            _n, _r
        ) for _n, _r in res_block.items() if _n not in _r_block)
        _update = dict((
            _n, _r
        ) for _n, _r in res_block.items() if _n in _r_block)

        if _add:
            _n_new = len(_add)
            _n_vbs = sum(r.num_vbo for r in _add.values())

            _vas = glGenVertexArrays(_n_new)  # vao
            _vbs = glGenBuffers(_n_vbs)  # vbo
            _ebs = glGenBuffers(_n_new)  # ebo

            if _n_new == 1:
                _vas, _ebs = [_vas], [_ebs]

            _n_vbo_st = 0
            for _ct, (_n, _r) in enumerate(_add.items()):  # name, resource
                _n_vbo_end = _n_vbo_st + _r.num_vbo
                _pick = list(_vbs[_n_vbo_st:_n_vbo_end])

                _r_obj = self.__Bind_geom__(_vas[_ct], _pick, _ebs[_ct], _r)
                _r_block[_n] = _r_obj
                _s_table[_r_obj.shader_name].append(_n)

                _n_vbo_st = _n_vbo_end

        if _update:
            # Todo: update 과정에서 vbs의 크기 변화에 대하여 확인 필요.
            for _n, _r in _update.items():  # name, resource
                _obj = _r_block[_n]
                _u_obj = self.__Bind_geom__(_obj.va, _obj.vbs, _obj.eb, _r)

                if _obj.shader_name != _u_obj.shader_name:
                    _s_table[_obj.shader_name].remove(_n)
                    _s_table[_u_obj.shader_name].append(_n)

                _r_block[_n] = _u_obj

    def Del_geometry(self, name_list: list[str]):
        _block = self.render_block
        _shader_table = self.shader_to_name_map

        _vao_list = []
        _vbo_list = []
        _ebo_list = []

        for _name in name_list:
            _b = _block.pop(_name)

            _vao_list.append(_b.va)
            _vbo_list.extend(_b.vbs)

            if _b.buffer:
                for _v in _b.buffer.values():
                    _vbo_list.extend(_v)

            if _b.eb is not None:
                _ebo_list.append(_b.eb)

            _shader = _b.shader_name
            _shader_table[_shader].remove(_name)

        glDeleteVertexArrays(len(_vao_list), _vao_list)
        glDeleteBuffers(len(_vbo_list), _vbo_list)
        glDeleteBuffers(len(_ebo_list), _ebo_list)

    # render
    def __Init_background__(self):
        glClearColor(*self.background)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def __Render_each_obj__(
        self, shader: ShaderProgram, render_obj: Render_Object
    ):
        _m_matrix = render_obj.m_matrix
        _p_model = glGetUniformLocation(shader, "model")
        glUniformMatrix4fv(_p_model, 1, GL_FALSE, _m_matrix)

        # call vao
        glBindVertexArray(render_obj.va)
        _mode = Const.Primitive_Mode[render_obj.mode]

        if render_obj.instance_count:
            _ct = render_obj.instance_count
            glDrawArraysInstanced(_mode, 0, 4, _ct)
        elif render_obj.index_count:
            _ct = render_obj.index_count
            glDrawElements(_mode, _ct, GL_UNSIGNED_INT, None)
        elif render_obj.vertex_count:
            _ct = render_obj.vertex_count
            glDrawArrays(_mode, 0, _ct)

    def __Depth_sort_for_3dgs__(
        self, obj: Render_Object, cam_view: np.ndarray,
        ping_pong: int,
        shaders: tuple[ShaderProgram, ShaderProgram, ShaderProgram] # depth, sort, reorder
    ):
        """3DGS 데이터에 대한 깊이 정렬 컴퓨트 패스를 실행합니다."""
        _d, _s, _o = shaders
        _num_gs = obj.instance_count

        if _num_gs == 0:
            return

        _f_id = ping_pong
        _t_id = 1 - ping_pong

        # depth
        glUseProgram(_d)
        glUniformMatrix4fv(
            glGetUniformLocation(_d, "view_matrix"), 1, GL_FALSE, cam_view)

        _from_pos = obj.vbs[_f_id]  # pos's id, that in vbs, is 0 or 1
        _from_ssbo = obj.buffer["ssbos"][_t_id]

        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, _from_pos)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, _from_ssbo)

        num_groups = (_num_gs + 1024 - 1) // 1024
        glDispatchCompute(num_groups, 1, 1)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        # Sort
        glUseProgram(_s)
        # 정렬은 목적지 SSBO 상에서 in-place로 수행됨
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, _from_ssbo)

        num_stages = (_num_gs - 1).bit_length()
        for stage in range(num_stages):
            glUniform1ui(glGetUniformLocation(_s, "stage"), stage)
            for sub_stage in range(stage, -1, -1):
                glUniform1ui(glGetUniformLocation(_s, "sub_stage"), sub_stage)
                glDispatchCompute(num_groups, 1, 1)
                glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        # re-oder
        glUseProgram(_o)
        # 입력: 정렬된 SSBO, 소스 VBO들
        # 출력: 목적지 VBO들
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, _from_ssbo)

        # 5개 속성(pts, clrs, ...)에 대해 반복
        for _ct in range(5):
            source_vbo = obj.vbs[_ct * 2 + _f_id]
            dest_vbo = obj.vbs[_ct * 2 + _t_id]
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1 + _ct, source_vbo)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 6 + _ct, dest_vbo)

        glDispatchCompute(num_groups, 1, 1)
        glMemoryBarrier(GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)

    def Render(self, camera, ping_pong: int = 1):
        self.__Init_background__()

        _geo_block = self.render_block
        _shader_to_name_map = self.shader_to_name_map
        _shader_block = self.shader_program

        _c_view = camera.get_view_matrix()
        _c_proj = camera.get_projection_matrix()

        # compute process

        # 3dgs
        _name_list = _shader_to_name_map["3dgs"]
        _shader_for_depth_sort = (
            _shader_block["bitonic_sort"],
            _shader_block["depth_calc"],
            _shader_block["reorder_data"]
        )

        for _name in _name_list:
            self.__Depth_sort_for_3dgs__(
                _geo_block[_name], _c_view, ping_pong, _shader_for_depth_sort
            )

        # render process

        for _shader_name, _name_list in _shader_to_name_map.items():
            # init shader program
            _p = _shader_block[_shader_name]

            glUseProgram(_p)
            _p_view = glGetUniformLocation(_p, "view")
            glUniformMatrix4fv(_p_view, 1, GL_FALSE, _c_view)
            _p_proj = glGetUniformLocation(_p, "projection")
            glUniformMatrix4fv(_p_proj, 1, GL_FALSE, _c_proj)

            if _shader_name == "3dgs":
                _focal_length = camera.get_focal_length()  # fx, fy
                _p_length = glGetUniformLocation(_p, "focal_length")
                glUniform2f(_p_length, *_focal_length)

            # render each obj
            for _name in _name_list:
                _obj = _geo_block[_name]
                self.__Render_each_obj__(_p, _obj)
        glBindVertexArray(0)

        return 1 - ping_pong


if __name__ == "__main__":
    print("debug")
    print("end")
