from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import glViewport

from vision_toolbox.asset import Scene
from .renderer import Scene_Manager


class ViewerWidget(QOpenGLWidget):
    """PyQt6 QOpenGLWidget을 상속받는 3D 뷰어 위젯."""
    initialized = Signal()
    camera_moved = Signal()

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)
        self.last_mouse_pos = QPoint()
        self._gl_initialized: bool = False
        self._pending_scene: Scene | None = None

        # Scene_Manager가 렌더러와 씬 데이터 관리를 모두 담당합니다.
        self.scene_manager = Scene_Manager.From_default(
            self.width(), self.height()
        )

    def initializeGL(self):
        """위젯 생성 시 한 번 호출: 렌더러 초기화."""
        self.scene_manager.Initialize_renderer()
        self._gl_initialized = True
        
        if self._pending_scene is not None:
            self.scene_manager.Set_scene(self._pending_scene)
            self._pending_scene = None
        
        self.initialized.emit()

    def Set_scene(self, scene: Scene):
        """렌더링할 새로운 씬을 설정합니다."""
        if not self._gl_initialized:
            # GL이 초기화되기 전에 씬이 설정되면, 나중에 설정하기 위해 저장
            self._pending_scene = scene
            return
        
        self.scene_manager.Set_scene(scene)
        self.update()

    def resizeGL(self, w: int, h: int):
        glViewport(0, 0, w, h)
        if self._gl_initialized:
            self.scene_manager.view_cam.Set_projection(w, h)

    def paintGL(self):
        """화면을 다시 그려야 할 때마다 호출됩니다."""
        if not self._gl_initialized:
            return
        self.scene_manager.Render_scene()

    # --- 이벤트 핸들러 ---
    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        _dx = event.pos().x() - self.last_mouse_pos.x()
        _dy = event.pos().y() - self.last_mouse_pos.y()
        _buttons = event.buttons()
        
        if _buttons & Qt.MouseButton.LeftButton:
            self.scene_manager.view_cam.Rotate(_dx, _dy)
        elif _buttons & Qt.MouseButton.RightButton:
            self.scene_manager.view_cam.Move(0, _dx, -_dy, sensitivity=0.01)

        self.last_mouse_pos = event.pos()
        self.update()
        self.camera_moved.emit()

    def wheelEvent(self, event):
        _scroll_delta = event.angleDelta().y() / 120.0
        self.scene_manager.view_cam.Move(_scroll_delta, 0, 0, sensitivity=0.2)
        self.update()
        self.camera_moved.emit()
