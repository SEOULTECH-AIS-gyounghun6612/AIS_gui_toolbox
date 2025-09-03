"""
gui_toolbox 렌더러 사용법을 보여주는 메인 예제 스크립트.

이 스크립트는 PySide6 애플리케이션을 설정하고,
3D 렌더링을 위한 ViewerWidget과 실시간 카메라 제어 UI를 포함하는
메인 윈도우를 생성합니다.
"""
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QComboBox, QCheckBox
)
from scipy.spatial.transform import Rotation as R
import open3d as o3d

from gui_toolbox import Application_Starter, Main_Window
from gui_toolbox.widget import ViewerWidget
from gui_toolbox.renderer import (
    Resource,
    Obj_Type,
    Sorter_Type,
    Create_random_3DGS,
    Create_axis_3DGS
)


class Render_Example_Window(Main_Window):
    """
    OpenGL 뷰어 위젯과 동적 컨트롤 UI를 포함하는 메인 윈도우 클래스.
    """
    def __Initialize_data__(self, **kwarg):
        """데이터 관련 초기화."""
        self.random_dgs_count = 0
        self.random_points_count = 0

    def __Initialize_interface__(self, **kwarg):
        """UI 초기화. 뷰어, 버튼, 카메라 컨트롤 패널을 생성하고 배치합니다."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        self.viewer = ViewerWidget(parent=self, sorter_type=Sorter_Type.OPENGL)
        controls_panel = self.__Create_controls_panel()

        main_layout.addWidget(self.viewer, 3)
        main_layout.addWidget(controls_panel, 1)

        self.viewer.initialized.connect(self.on_viewer_ready)
        self.viewer.camera_moved.connect(self._update_ui_from_camera)

    def __Create_controls_panel(self) -> QWidget:
        """모든 컨트롤 UI 위젯을 생성하고 패널에 배치합니다."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(self.__Create_object_controls())
        layout.addWidget(self.__Create_abs_camera_controls())
        layout.addWidget(self.__Create_rel_camera_controls())
        layout.addStretch(1)
        return panel

    def __Create_object_controls(self) -> QGroupBox:
        group = QGroupBox("Add Objects")
        layout = QHBoxLayout(group)
        add_axis_btn = QPushButton("Add Axis")
        add_random_btn = QPushButton("Add Random Gaussians")
        add_points_btn = QPushButton("Add Random Points")
        layout.addWidget(add_axis_btn)
        layout.addWidget(add_random_btn)
        layout.addWidget(add_points_btn)
        add_axis_btn.clicked.connect(self.add_axis)
        add_random_btn.clicked.connect(self.add_random_gaussians)
        add_points_btn.clicked.connect(self.add_random_points)
        return group

    def __Create_abs_camera_controls(self) -> QGroupBox:
        group = QGroupBox("Absolute Camera Pose")
        layout = QGridLayout(group)

        self.dx_spin = QDoubleSpinBox(); self.dx_spin.setRange(-1000, 1000); self.dx_spin.setSingleStep(0.1)
        self.dy_spin = QDoubleSpinBox(); self.dy_spin.setRange(-1000, 1000); self.dy_spin.setSingleStep(0.1)
        self.dz_spin = QDoubleSpinBox(); self.dz_spin.setRange(-1000, 1000); self.dz_spin.setSingleStep(0.1)
        self.yaw_spin = QDoubleSpinBox(); self.yaw_spin.setRange(-360, 360); self.yaw_spin.setWrapping(True)
        self.pitch_spin = QDoubleSpinBox(); self.pitch_spin.setRange(-89, 89); self.pitch_spin.setWrapping(False)
        
        self.pose_controls = [self.dx_spin, self.dy_spin, self.dz_spin, self.yaw_spin, self.pitch_spin]

        layout.addWidget(QLabel("Pos (x,y,z):"), 0, 0)
        layout.addWidget(self.dx_spin, 0, 1); layout.addWidget(self.dy_spin, 0, 2); layout.addWidget(self.dz_spin, 0, 3)
        layout.addWidget(QLabel("Rot (Yaw, Pitch):"), 1, 0)
        layout.addWidget(self.yaw_spin, 1, 1); layout.addWidget(self.pitch_spin, 1, 2)

        self.track_pose_checkbox = QCheckBox("Track Current Pose")
        self.track_pose_checkbox.setChecked(True)
        layout.addWidget(self.track_pose_checkbox, 3, 0, 1, 4)

        for control in self.pose_controls:
            control.valueChanged.connect(self._update_camera_from_ui)
        
        return group

    def __Create_rel_camera_controls(self) -> QGroupBox:
        group = QGroupBox("Relative Camera Movement")
        layout = QGridLayout(group)
        
        self.move_step_spin = QDoubleSpinBox(); self.move_step_spin.setRange(0.01, 10); self.move_step_spin.setSingleStep(0.1); self.move_step_spin.setValue(0.2)
        layout.addWidget(QLabel("Move Step:"), 0, 0)
        layout.addWidget(self.move_step_spin, 0, 1)

        btn_fwd = QPushButton("Forward"); btn_bwd = QPushButton("Backward")
        btn_l = QPushButton("Left"); btn_r = QPushButton("Right")
        btn_u = QPushButton("Up"); btn_d = QPushButton("Down")
        
        btn_fwd.clicked.connect(lambda: self._move_relative('forward'))
        btn_bwd.clicked.connect(lambda: self._move_relative('backward'))
        btn_l.clicked.connect(lambda: self._move_relative('left'))
        btn_r.clicked.connect(lambda: self._move_relative('right'))
        btn_u.clicked.connect(lambda: self._move_relative('up'))
        btn_d.clicked.connect(lambda: self._move_relative('down'))

        layout.addWidget(btn_fwd, 1, 1); layout.addWidget(btn_u, 1, 2)
        layout.addWidget(btn_l, 2, 0); layout.addWidget(btn_r, 2, 2)
        layout.addWidget(btn_bwd, 3, 1); layout.addWidget(btn_d, 3, 2)
        return group

    def _update_camera_from_ui(self):
        if self.track_pose_checkbox.isChecked():
            return

        self.viewer.camera.position[0] = self.dx_spin.value()
        self.viewer.camera.position[1] = self.dy_spin.value()
        self.viewer.camera.position[2] = self.dz_spin.value()
        self.viewer.camera.yaw = self.yaw_spin.value()
        self.viewer.camera.pitch = self.pitch_spin.value()
        self.viewer.camera._View_Cam__Update_view_mat() # Private method call, but necessary here
        self.viewer.update()

    def _update_ui_from_camera(self):
        if not self.track_pose_checkbox.isChecked():
            return

        pos = self.viewer.camera.position
        yaw = self.viewer.camera.yaw
        pitch = self.viewer.camera.pitch
        
        controls = [self.dx_spin, self.dy_spin, self.dz_spin, self.yaw_spin, self.pitch_spin]
        values = [pos[0], pos[1], pos[2], yaw, pitch]

        for control, value in zip(controls, values):
            control.blockSignals(True)
            control.setValue(value)
            control.blockSignals(False)

    def _move_relative(self, direction: str):
        step = self.move_step_spin.value()
        if direction == 'forward':   self.viewer.camera.Move(step, 0, 0)
        elif direction == 'backward':self.viewer.camera.Move(-step, 0, 0)
        elif direction == 'left':    self.viewer.camera.Move(0, -step, 0)
        elif direction == 'right':   self.viewer.camera.Move(0, step, 0)
        elif direction == 'up':      self.viewer.camera.Move(0, 0, step)
        elif direction == 'down':    self.viewer.camera.Move(0, 0, -step)
        self.viewer.update()

    def on_viewer_ready(self):
        print("Viewer is initialized and ready.")
        self._update_ui_from_camera()

    def add_axis(self):
        print("Adding axis asset.")
        self.viewer.add_asset({
            "axis": Resource(
                obj_type=Obj_Type.GAUSSIAN_SPLAT,
                data=Create_axis_3DGS()
            )
        })

    def add_random_gaussians(self):
        self.random_dgs_count += 1
        new_name = f"random_dgs_{self.random_dgs_count}"
        print(f"Adding new asset: {new_name}")
        self.viewer.add_asset({
            new_name: Resource(
                obj_type=Obj_Type.GAUSSIAN_SPLAT,
                data=Create_random_3DGS(num_points=2000)
            )
        })

    def add_random_points(self):
        self.random_points_count += 1
        new_name = f"random_points_{self.random_points_count}"
        print(f"Adding new asset: {new_name}")
        
        # Create random points
        points = np.random.rand(1000, 3) * 2 - 1  # Random points in [-1, 1] cube
        
        # Create Open3D PointCloud
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        self.viewer.add_asset({
            new_name: Resource(
                obj_type=Obj_Type.POINTS,
                data=pcd
            )
        })

    def Run(self):
        print("Render_Example_Window is running.")

    def Stop(self):
        print("Render_Example_Window is stopping.")


def main():
    starter = Application_Starter()
    main_window = Render_Example_Window(
        title="Renderer Example with Interactive Camera Controls",
        position=(100, 100, 1600, 900)
    )
    starter.Start(main_window)


if __name__ == "__main__":
    main()