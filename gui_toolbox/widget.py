import numpy as np

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import glViewport

from .renderer import (
    View_Cam, OpenGL_Renderer, Resource, Render_Opt,
    Clear_Opt, Sorter_Type
)


CV_TO_GL = np.array([
    [1,0,0,0], [0,-1,0,0], [0,0,-1,0], [0,0,0,1]
], dtype=np.float32)


class ViewerWidget(QOpenGLWidget):
    """PyQt6 QOpenGLWidget을 상속받는 3D 뷰어 위젯"""
    initialized = Signal()

    def __init__(
        self,
        parent=None,
        bg_color: tuple = (0.5, 0.5, 0.5, 1.0),
        enable_opts: tuple[Render_Opt, ...] | None = None,
        clear_mask: Clear_Opt = Clear_Opt.COLOR | Clear_Opt.DEPTH,
        sorter_type: Sorter_Type = Sorter_Type.OPENGL
    ):
        super().__init__(parent)
        self.camera = View_Cam(self.width(), self.height())
        self.last_mouse_pos = QPoint()
        
        self._gl_initialized: bool = False
        self._pending_assets: dict[str, Resource] = {}

        _opts = enable_opts if enable_opts is not None else (
            Render_Opt.DEPTH, Render_Opt.BLEND,
            Render_Opt.MULTISAMPLE_AA, Render_Opt.P_ABLE_P_SIZE
        )
        self.renderer = OpenGL_Renderer(
            bg_color=bg_color,
            enable_opts=_opts,
            clear_mask=clear_mask,
            sorter_type=sorter_type
        )

    def initializeGL(self):
        """위젯 생성 시 한 번 호출: 렌더러 초기화 및 대기 중인 에셋 처리."""
        self.renderer.initialize()
        self._gl_initialized = True

        if self._pending_assets:
            self.add_asset(self._pending_assets)
            self._pending_assets = {}
        
        self.initialized.emit()

    def add_asset(self, data: dict[str, Resource]):
        """렌더링할 에셋을 추가하거나 업데이트합니다."""
        if not self._gl_initialized:
            self._pending_assets.update(data)
            return
        
        self.renderer.Set_resources(data)
        self.update()

    def resizeGL(self, w: int, h: int):
        glViewport(0, 0, w, h)
        self.camera.Set_projection(w, h)

    def paintGL(self):
        """화면을 다시 그려야 할 때마다 호출됩니다."""
        if not self._gl_initialized:
            return
        self.renderer.Render(self.camera)

    def cleanup(self):
        """Cleans up OpenGL resources. Must be called before the widget is destroyed."""
        if self._gl_initialized:
            self.makeCurrent()
            self.renderer.cleanup()
            self.doneCurrent()

    # --- 이벤트 핸들러 ---
    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.pos().x() - self.last_mouse_pos.x()
        dy = event.pos().y() - self.last_mouse_pos.y()
        buttons = event.buttons()
        
        if buttons & Qt.MouseButton.LeftButton:
            self.camera.Tilt(dx, dy)
        elif buttons & Qt.MouseButton.RightButton:
            self.camera.Pan(dx, dy)

        self.last_mouse_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        self.camera.Zoom(event.angleDelta().y())
        self.update()
