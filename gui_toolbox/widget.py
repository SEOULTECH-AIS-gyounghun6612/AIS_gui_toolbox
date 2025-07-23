import numpy as np

from open3d import geometry, utility

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import glViewport

# 테스트 데이터 생성을 위해 open3d 임포트
# import open3d as o3d

# 제공된 렌더러 모듈 및 데이터 클래스 임포트
from .utils.renderer.scene import (
    View_Cam, Create_dummy_3DGS
)
from .utils.renderer.render import (
    OpenGL_Renderer, Resource,
    Render_Opt, Clear_Opt, Obj_Type, Draw_Opt
)


CV_TO_GL = np.array([
    [1,0,0,0],
    [0,-1,0,0],
    [0,0,-1,0],
    [0,0,0,1]
], dtype=np.float32)


class ViewerWidget(QOpenGLWidget):
    """PyQt6 QOpenGLWidget을 상속받는 3D 뷰어 위젯"""
    def __init__(
        self,
        parent=None,
        bg_color: tuple = (0.5, 0.5, 0.5, 1.0),
        enable_opts: tuple[Render_Opt, ...] | None = None,
        clear_mask: Clear_Opt = Clear_Opt.COLOR | Clear_Opt.DEPTH
    ):
        super().__init__(parent)
        self.camera = View_Cam(self.width(), self.height())
        self.last_mouse_pos = QPoint()
        self.resources: dict[str, Resource] = {}

        _opts = enable_opts if enable_opts is not None else (
            Render_Opt.DEPTH,
            Render_Opt.BLEND,
            Render_Opt.MULTISAMPLE_AA,
            Render_Opt.P_ABLE_P_SIZE
        )
        self.renderer = OpenGL_Renderer(
            bg_color=bg_color,
            enable_opts=_opts,
            clear_mask=clear_mask
        )

    def initializeGL(self):
        """위젯 생성 시 한 번 호출: 렌더러 초기화."""
        self.renderer.initialize()

        # debug
        _test_data = Create_dummy_3DGS()

        _test_pc = geometry.PointCloud()
        _test_pc.points = utility.Vector3dVector(_test_data.points)
        _test_pc.colors = utility.Vector3dVector(_test_data.colors)

        self.add_asset({
            "test_3dgs": Resource(
                obj_type=Obj_Type.GAUSSIAN_SPLAT,
                data=_test_data,
                draw_opt=Draw_Opt.DYNAMIC
            ),
            "test_pc": Resource(
                obj_type=Obj_Type.TRAJ, # TRAJ Enum 사용
                data=_test_pc, 
                draw_opt=Draw_Opt.STATIC
            )
        })

    def add_asset(self, data: dict[str, Resource]):
        self.renderer.Set_resources(data)
        self.update() # 화면 갱신 요청

    def resizeGL(self, w: int, h: int):
        glViewport(0, 0, w, h)
        self.camera.Set_projection(w, h)

    def paintGL(self):
        """화면을 다시 그려야 할 때마다 호출됩니다."""
        self.renderer.Render(self.camera)
        # [수정] 여기서 self.update()를 호출하면 무한 루프에 빠지므로 제거합니다.

    # --- 이벤트 핸들러 ---
    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.pos().x() - self.last_mouse_pos.x()
        dy = event.pos().y() - self.last_mouse_pos.y()

        buttons = event.buttons()
        modifiers = event.modifiers()

        if buttons & Qt.MouseButton.LeftButton:
            self.camera.Tilt(dx, dy)
        elif buttons & Qt.MouseButton.RightButton:
            self.camera.Pan(dx, dy)

        self.last_mouse_pos = event.pos()
        self.update() # [이동] 카메라 상태가 변경되었으므로 여기서 화면 갱신을 요청합니다.

    def wheelEvent(self, event):
        self.camera.Zoom(event.angleDelta().y())
        self.update() # [이동] 카메라 상태가 변경되었으므로 여기서 화면 갱신을 요청합니다.