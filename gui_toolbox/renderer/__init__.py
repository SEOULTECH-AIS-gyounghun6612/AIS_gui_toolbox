"""
gui_toolbox.renderer 패키지

OpenGL 렌더러와 관련 유틸리티, 데이터 구조를 제공합니다.
이 `__init__.py` 파일은 패키지의 주요 구성 요소들을 최상위 네임스페이스로 노출하여
사용자가 쉽게 임포트할 수 있도록 돕는 공개 API 역할을 합니다.
"""

# --- Public API 노출 ---

# 핵심 렌더러 클래스
from .render import OpenGL_Renderer

# 렌더링 데이터 및 카메라/장면 관리
from .scene_manager import (
    View_Cam, Scene_Manager,
    Create_dummy_scene
)

# 렌더링에 필요한 데이터 구조 및 Enum 타입
from .definitions import (
    # Data Structures
    Resource,
    Render_Object,
    O3D_GEOMETRY,
    # Enums for OpenGL
    Draw_Opt,
    Render_Opt,
    Clear_Opt,
    Prim,
    Buf_Name,
    # Enums for Logic
    Sorter_Type,
    Shader_Type,
    Obj_Type,
    # Constants
    DEFAULT_RENDER_OPT
)

# 네임스페이스로 구조화된 핸들러 및 소터
from .handler import Sorter, Handler

# 핵심 유틸리티 함수
from .definitions import (
    Build_rnd,
    Build_compute,
    Create_uniform_setter
)
