"""Renderer 패키지에서 사용되는 공통 데이터 구조, Enum 및 유틸리티 함수 모음."""

from typing import Union, Any
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path
from enum import IntEnum, StrEnum, IntFlag

import numpy as np
from OpenGL.GL import (
    GL_POINTS, GL_LINES, GL_LINE_STRIP, GL_LINE_LOOP,
    GL_TRIANGLES, GL_TRIANGLE_STRIP, GL_TRIANGLE_FAN,
    GL_DEPTH_TEST, GL_BLEND, GL_CULL_FACE,
    GL_PROGRAM_POINT_SIZE, GL_MULTISAMPLE,
    GL_STATIC_DRAW, GL_DYNAMIC_DRAW,
    GL_ARRAY_BUFFER, GL_ELEMENT_ARRAY_BUFFER, GL_SHADER_STORAGE_BUFFER,
    GL_VERTEX_SHADER, GL_FRAGMENT_SHADER, GL_COMPUTE_SHADER,
    glGetUniformLocation, glUniformMatrix4fv, glUniform3fv, glUniform2fv,
    glUniform1ui, glUniform1i, glUniform1f, GL_FALSE,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_STENCIL_BUFFER_BIT,
)
from OpenGL.GL.shaders import ShaderProgram, compileProgram, compileShader
from open3d import geometry

from vision_toolbox.asset import Gaussian_3DGS
from vision_toolbox.utils import geometry as Geo_Utils


# --- Enums for OpenGL Options ---

class Draw_Opt(IntEnum):
    """glBufferData의 드로우 옵션"""
    STATIC = GL_STATIC_DRAW
    DYNAMIC = GL_DYNAMIC_DRAW

class Render_Opt(IntEnum):
    """glEnable/glDisable에 사용되는 렌더링 옵션"""
    DEPTH = GL_DEPTH_TEST
    BLEND = GL_BLEND
    FACE_CULL = GL_CULL_FACE
    P_ABLE_P_SIZE = GL_PROGRAM_POINT_SIZE
    MULTISAMPLE_AA = GL_MULTISAMPLE

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

# --- Enums for Renderer Logic ---

class Sorter_Type(StrEnum):
    """3DGS 소터 타입 정의"""
    OPENGL = "opengl"
    TORCH = "torch"
    CPU = "cpu"

class Shader_Type(StrEnum):
    GAUSSIAN_SPLAT = "3dgs"
    SIMPLE = "simple"

class Obj_Type(StrEnum):
    GAUSSIAN_SPLAT = "3dgs"
    TRAJ = "trajectory"
    POINTS = "points"

# --- Data Structures ---

O3D_GEOMETRY = Union[
    geometry.PointCloud, geometry.LineSet, geometry.TriangleMesh]

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
    cpu_data: dict[str, np.ndarray] | None = None  # For CPU/Torch sorters
    vtx_count: int = 0
    idx_count: int = 0
    inst_count: int = 0

    def Get_ids(self) -> tuple[int, list[int], int | None]:
        return self.vao, self.vbos, self.ebo

# --- Constants ---

OBJ_TO_SHADER: dict[Obj_Type, Shader_Type] = {
    Obj_Type.GAUSSIAN_SPLAT: Shader_Type.GAUSSIAN_SPLAT,
    Obj_Type.TRAJ: Shader_Type.SIMPLE,
    Obj_Type.POINTS: Shader_Type.SIMPLE
}

SHADER_TO_NUM_VBO: dict[Shader_Type, int] = {
    Shader_Type.GAUSSIAN_SPLAT: 0,
    Shader_Type.SIMPLE: 2
}

DEFAULT_RENDER_OPT = (
    Render_Opt.DEPTH, Render_Opt.BLEND,
    Render_Opt.P_ABLE_P_SIZE, Render_Opt.MULTISAMPLE_AA
)

# --- Core Utility Functions ---

def Create_splat_buffer(asset: Gaussian_3DGS) -> np.ndarray:
    """Gaussian_3DGS 에셋으로부터 std430 레이아웃에 맞는 SSBO 버퍼를 생성."""
    _num_3dgs = len(asset.points)
    if _num_3dgs == 0:
        return np.array([], dtype=np.float32)

    _covA, _covB = Geo_Utils.Compute_3d_covariance(asset.scales, asset.rotations)

    # 셰이더의 Splat 구조체 레이아웃에 맞게 수동으로 패딩하여 버퍼 생성
    # (vec3는 vec4처럼 16바이트 정렬됨)
    _buffer = np.zeros((_num_3dgs, 76), dtype=np.float32)
    _buffer[:, 0:3] = asset.points
    _buffer[:, 3] = asset.opacities.flatten()
    _buffer[:, 4:7] = _covA
    _buffer[:, 8:11] = _covB
    
    _sh_features = asset.sh_features.reshape(_num_3dgs, 16, 3)
    _sh_start_index = 12
    for i in range(16):
        _sh_slot = _sh_start_index + i * 4
        _buffer[:, _sh_slot:_sh_slot + 3] = _sh_features[:, i, :]
    
    return _buffer

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
    @lru_cache(maxsize=None)
    def get_loc(name):
        return glGetUniformLocation(shader_prog, name)

    def Set_mat4(name, value):
        glUniformMatrix4fv(get_loc(name), 1, GL_FALSE, value)

    def Set_vec3(name, value):
        glUniform3fv(get_loc(name), 1, value)

    def Set_vec2(name, value):
        glUniform2fv(get_loc(name), 1, value)

    def Set_uint(name, value):
        glUniform1ui(get_loc(name), value)

    def Set_int(name, value):
        glUniform1i(get_loc(name), value)

    def Set_float(name, value):
        glUniform1f(get_loc(name), value)

    def Set_bool(name, value):
        glUniform1i(get_loc(name), int(value))

    return {
        "mat4": Set_mat4,
        "vec3": Set_vec3,
        "vec2": Set_vec2,
        "uint": Set_uint,
        "int": Set_int,
        "float": Set_float,
        "bool": Set_bool
    }