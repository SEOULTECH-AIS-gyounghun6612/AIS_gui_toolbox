"""
gui_toolbox 렌더러 사용법을 보여주는 메인 예제 스크립트.

이 스크립트는 PySide6 애플리케이션을 설정하고,
리팩토링된 ViewerWidget을 사용하여 다양한 3D 에셋을 렌더링하는 방법을 보여줍니다.
"""
import sys
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QDockWidget, QPushButton, QDoubleSpinBox, QSizePolicy
)

from gui_toolbox.widget import ViewerWidget
from gui_toolbox.renderer import View_Cam
from vision_toolbox.asset import Scene, Gaussian_3DGS, Point_Cloud, Camera


def create_axis_gs_asset() -> Gaussian_3DGS:
    """좌표축을 나타내는 3DGS 에셋을 생성합니다."""
    _points = np.array([
        [0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]
    ], dtype=np.float32)
    _sh_dc = np.array([
        [1, 1, 1], [1, 0, 0], [0, 1, 0], [0, 0, 1]
    ], dtype=np.float32) # W, R, G, B
    _scales = np.array([
        [0.03, 0.03, 0.03], [0.2, 0.01, 0.01],
        [0.01, 0.2, 0.01], [0.01, 0.01, 0.2]
    ], dtype=np.float32)
    _rotations = np.zeros((4, 4), dtype=np.float32)
    _rotations[:, 3] = 1.0
    _opacities = np.ones((4, 1), dtype=np.float32)

    _sh_features = np.zeros((4, 16, 3), dtype=np.float32)
    _sh_features[:, 0, :] = _sh_dc

    return Gaussian_3DGS(
        relative_path="axis_gs.npz",
        points=_points,
        colors=(_sh_dc * 255).astype(np.uint8),
        opacities=_opacities,
        scales=_scales,
        rotations=_rotations,
        sh_features=_sh_features
    )

def create_random_gs_asset(num_points=1000) -> Gaussian_3DGS:
    """구 안에 무작위로 분포된 3DGS 에셋을 생성합니다."""
    _pts = np.random.randn(num_points, 3).astype(np.float32)
    _sh_dc = np.random.rand(num_points, 3).astype(np.float32)
    _opacities = np.random.uniform(0.8, 1.0, (num_points, 1)).astype(np.float32)
    _scales = np.random.uniform(0.01, 0.05, (num_points, 3)).astype(np.float32)
    _rotations = np.zeros((num_points, 4), dtype=np.float32)
    _rotations[:, 3] = 1.0

    _sh_features = np.zeros((num_points, 16, 3), dtype=np.float32)
    _sh_features[:, 0, :] = _sh_dc

    return Gaussian_3DGS(
        relative_path="random_gs.npz",
        points=_pts,
        colors=(_sh_dc * 255).astype(np.uint8),
        opacities=_opacities,
        scales=_scales,
        rotations=_rotations,
        sh_features=_sh_features
    )

def create_random_points_asset(num_points=1000) -> Point_Cloud:
    """무작위 점군 에셋을 생성합니다."""
    _pts = (np.random.rand(num_points, 3) * 2 - 1).astype(np.float32)
    _colors = (np.random.rand(num_points, 3) * 255).astype(np.uint8)
    return Point_Cloud(
        relative_path="random_points.npz",
        points=_pts,
        colors=_colors
    )


class ControlPanelWidget(QWidget):
    """카메라와 에셋 정보를 보여주고 제어하는 통합 패널 위젯."""
    def __init__(self, viewer_widget: ViewerWidget, parent=None):
        super().__init__(parent)
        self.viewer = viewer_widget
        self.view_cam = self.viewer.scene_manager.view_cam
        self._updating_ui = False

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        cam_group = self._create_camera_control_group()
        main_layout.addWidget(cam_group)

        asset_group = self._create_asset_info_group()
        main_layout.addWidget(asset_group)

        main_layout.addStretch()

        self.viewer.camera_moved.connect(self.update_camera_ui)

    def _create_camera_control_group(self) -> QGroupBox:
        group_box = QGroupBox("Camera Control")
        layout = QVBoxLayout()

        # Position
        pos_layout = QGridLayout()
        self.pos_spins = []
        for i, label in enumerate(["X", "Y", "Z"]):
            pos_layout.addWidget(QLabel(label), 0, i*2)
            spin = QDoubleSpinBox()
            spin.setRange(-1000, 1000)
            spin.setDecimals(2)
            spin.setSingleStep(0.1)
            spin.valueChanged.connect(self.on_camera_transform_changed)
            pos_layout.addWidget(spin, 0, i*2 + 1)
            self.pos_spins.append(spin)
        
        # Rotation
        rot_layout = QHBoxLayout()
        self.rot_spins = []
        for i, label in enumerate(["Yaw", "Pitch"]):
            rot_layout.addWidget(QLabel(label))
            spin = QDoubleSpinBox()
            spin.setRange(-360, 360)
            spin.setDecimals(2)
            spin.setSingleStep(1)
            spin.valueChanged.connect(self.on_camera_transform_changed)
            rot_layout.addWidget(spin)
            self.rot_spins.append(spin)

        # Movement Buttons
        move_layout = QGridLayout()
        buttons = {
            "Forward": (0, 1, lambda: self.on_move_button_clicked(fwd=1)),
            "Backward": (2, 1, lambda: self.on_move_button_clicked(fwd=-1)),
            "Left": (1, 0, lambda: self.on_move_button_clicked(right=-1)),
            "Right": (1, 2, lambda: self.on_move_button_clicked(right=1)),
            "Up": (0, 2, lambda: self.on_move_button_clicked(up=1)),
            "Down": (2, 2, lambda: self.on_move_button_clicked(up=-1)),
        }
        for name, (r, c, handler) in buttons.items():
            btn = QPushButton(name)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(handler)
            move_layout.addWidget(btn, r, c)

        layout.addLayout(pos_layout)
        layout.addLayout(rot_layout)
        layout.addLayout(move_layout)
        group_box.setLayout(layout)
        return group_box

    def _create_asset_info_group(self) -> QGroupBox:
        group_box = QGroupBox("Asset Info")
        layout = QVBoxLayout()
        self.asset_type_label = QLabel("Type: N/A")
        self.asset_points_label = QLabel("Points: N/A")
        layout.addWidget(self.asset_type_label)
        layout.addWidget(self.asset_points_label)
        group_box.setLayout(layout)
        return group_box

    def update_camera_ui(self):
        if self.view_cam:
            self._updating_ui = True
            pos = self.view_cam.cam_data.pose[:3, 3]
            for i in range(3):
                self.pos_spins[i].setValue(pos[i])
            
            self.rot_spins[0].setValue(self.view_cam.yaw)
            self.rot_spins[1].setValue(self.view_cam.pitch)
            self._updating_ui = False

    def on_camera_transform_changed(self):
        if self.view_cam and not self._updating_ui:
            # Update position
            new_pos = np.array([s.value() for s in self.pos_spins], dtype=np.float32)
            self.view_cam.cam_data.pose[:3, 3] = new_pos
            
            # Update rotation (This is more complex, direct yaw/pitch manipulation is safer)
            # For now, we let mouse control rotation primarily. Re-evaluating direct input.
            # Let's just update position for now. Direct rotation update is tricky.
            
            self.view_cam._Update_derived_props_from_pose()
            self.viewer.update()
            self.update_camera_ui()

    def on_move_button_clicked(self, fwd=0, right=0, up=0):
        if self.view_cam:
            self.view_cam.Move(fwd, right, up, sensitivity=0.1)
            self.viewer.update()

    def update_asset_ui(self, scene: Scene):
        if not scene or not scene.assets:
            self.asset_type_label.setText("Type: N/A")
            self.asset_points_label.setText("Points: N/A")
            return

        # 첫 번째 에셋 정보 표시
        asset_name = next(iter(scene.assets))
        asset = scene.assets[asset_name]
        
        asset_type = type(asset).__name__
        num_points = len(asset.points) if hasattr(asset, 'points') else 'N/A'

        self.asset_type_label.setText(f"Type: {asset_type}")
        self.asset_points_label.setText(f"Points: {num_points}")


class Example_Window(QMainWindow):
    """ViewerWidget을 중앙에 배치하고 정보 위젯을 추가하는 메인 윈도우."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GUI Toolbox - Full Control Example")
        self.setGeometry(100, 100, 1600, 900)

        self.viewer = ViewerWidget(parent=self)
        self.setCentralWidget(self.viewer)

        self._setup_control_dock()

    def _setup_control_dock(self):
        """카메라 및 에셋 제어판을 위한 Dock Widget을 설정합니다."""
        self.control_panel = ControlPanelWidget(self.viewer)
        dock_widget = QDockWidget("Control Panel", self)
        dock_widget.setWidget(self.control_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)
        
        # GL 초기화 후 UI 업데이트
        self.viewer.initialized.connect(self.control_panel.update_camera_ui)

    def set_scene(self, scene: Scene):
        """씬을 설정하고 UI를 업데이트합니다."""
        self.viewer.Set_scene(scene)
        
        # 디버깅을 위해 월드 좌표축을 추가합니다.
        self.viewer.scene_manager.Add_axis(name="world_axis", size=1.0)

        # 씬에 있는 카메라의 위치를 기반으로 궤적을 추가합니다.
        self.viewer.scene_manager.Add_trajectory(
            name="camera_trajectory",
            color=(1.0, 1.0, 0.0)  # Yellow color
        )

        self.control_panel.update_asset_ui(scene)
        self.control_panel.update_camera_ui()


def main():
    """애플리케이션을 설정하고 실행합니다."""
    app = QApplication(sys.argv)
    
    window = Example_Window()

    # --- 렌더링할 씬(Scene)을 구성합니다. ---
    # asset_to_show = create_axis_gs_asset()
    asset_to_show = create_random_gs_asset(5000)
    # asset_to_show = create_random_points_asset(5000)

    scene = Scene(
        name="example_scene",
        assets={"debug_asset": asset_to_show}
    )

    # --- 테스트용 카메라들을 씬에 추가합니다. ---
    num_cameras = 10
    cameras = {}
    for i in range(num_cameras):
        pose = np.eye(4, dtype=np.float32)
        pose[0, 3] = np.cos(i * np.pi / 5) * 2  # X position in a circle
        pose[1, 3] = np.sin(i * np.pi / 5) * 2  # Y position in a circle
        pose[2, 3] = i * 0.3  # Z position moves up
        cam_name = f"cam_{i:03d}"
        cameras[cam_name] = Camera(
            name=cam_name,
            pose=pose,
            intrinsics=np.array(
                [[1100, 0, 800], [0, 1100, 450], [0, 0, 1]], dtype=np.float32
            ),
            image_size=np.array([1600, 900])
        )
    scene.cameras = cameras
    # ------------------------------------------

    # 위젯이 준비되면 Set_scene을 호출하도록 연결합니다.
    window.viewer.initialized.connect(lambda: window.set_scene(scene))
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
