"""
gui_toolbox 렌더러 사용법을 보여주는 메인 예제 스크립트.

이 스크립트는 PySide6 애플리케이션을 설정하고,
3D 렌더링을 위한 ViewerWidget과 카메라 제어 UI를 포함하는
메인 윈도우를 생성합니다.
"""
import numpy as np
import open3d as o3d
from PySide6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QComboBox
)
from scipy.spatial.transform import Rotation as R

from gui_toolbox import Application_Starter, Main_Window
from gui_toolbox.widget import ViewerWidget
from gui_toolbox.renderer import (
    Resource,
    Obj_Type,
    Sorter_Type,
    Create_random_3DGS
)


class Render_Example_Window(Main_Window):
    """
    OpenGL 뷰어 위젯과 컨트롤 UI를 포함하는 메인 윈도우 클래스.
    """
    def __Initialize_data__(self, **kwarg):
        """데이터 관련 초기화."""
        self.random_dgs_count = 0
        self.move_step = 0.2

    def __Initialize_interface__(self, **kwarg):
        """UI 초기화. 뷰어, 버튼, 카메라 컨트롤 패널을 생성하고 배치합니다."""
        # --- 1. 메인 레이아웃 설정 ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- 2. 왼쪽: 뷰어 및 기본 컨트롤 ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.viewer = ViewerWidget(parent=self, sorter_type=Sorter_Type.OPENGL)
        self.add_random_button = QPushButton("Add Random 3DGS")
        left_layout.addWidget(self.viewer)
        left_layout.addWidget(self.add_random_button)

        # --- 3. 오른쪽: 카메라 고급 컨트롤 ---
        controls_panel = self.__Create_camera_controls_panel()

        # --- 4. 메인 레이아웃에 패널 추가 ---
        main_layout.addWidget(left_panel, 3)  # 3/4 비율로 설정
        main_layout.addWidget(controls_panel, 1)  # 1/4 비율로 설정

        # --- 5. 시그널-슬롯 연결 ---
        self.add_random_button.clicked.connect(self.add_random_gaussians)
        self.viewer.initialized.connect(self.on_viewer_ready)

    def __Create_camera_controls_panel(self) -> QWidget:
        """카메라 제어를 위한 UI 위젯들을 생성하고 그룹화하여 반환합니다."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)

        # --- 절대 포즈 제어 그룹 ---
        abs_group = QGroupBox("Absolute Camera Pose")
        abs_layout = QGridLayout(abs_group)

        # Position and Rotation Spinboxes
        self.dx_spin = QDoubleSpinBox(); self.dx_spin.setRange(-100, 100); self.dx_spin.setSingleStep(0.1)
        self.dy_spin = QDoubleSpinBox(); self.dy_spin.setRange(-100, 100); self.dy_spin.setSingleStep(0.1)
        self.dz_spin = QDoubleSpinBox(); self.dz_spin.setRange(-100, 100); self.dz_spin.setSingleStep(0.1); self.dz_spin.setValue(5)
        self.rx_spin = QDoubleSpinBox(); self.rx_spin.setRange(-360, 360)
        self.ry_spin = QDoubleSpinBox(); self.ry_spin.setRange(-360, 360)
        self.rz_spin = QDoubleSpinBox(); self.rz_spin.setRange(-360, 360)

        abs_layout.addWidget(QLabel("Pos (dx,dy,dz):"), 0, 0)
        abs_layout.addWidget(self.dx_spin, 0, 1); abs_layout.addWidget(self.dy_spin, 0, 2); abs_layout.addWidget(self.dz_spin, 0, 3)
        abs_layout.addWidget(QLabel("Rot (rx,ry,rz):"), 1, 0)
        abs_layout.addWidget(self.rx_spin, 1, 1); abs_layout.addWidget(self.ry_spin, 1, 2); abs_layout.addWidget(self.rz_spin, 1, 3)

        # Rotation Order ComboBox
        self.rot_order_combo = QComboBox()
        self.rot_order_combo.addItems(['XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX'])
        abs_layout.addWidget(QLabel("Rotation Order:"), 2, 0)
        abs_layout.addWidget(self.rot_order_combo, 2, 1, 1, 3)

        # Apply Button
        apply_abs_button = QPushButton("Apply Absolute Pose")
        apply_abs_button.clicked.connect(self._apply_absolute_camera_pose)
        abs_layout.addWidget(apply_abs_button, 3, 0, 1, 4)

        # --- 상대 이동 제어 그룹 ---
        rel_group = QGroupBox("Relative Camera Movement")
        rel_layout = QGridLayout(rel_group)
        
        btn_fwd = QPushButton("Forward"); btn_fwd.clicked.connect(lambda: self._move_relative('forward'))
        btn_bwd = QPushButton("Backward"); btn_bwd.clicked.connect(lambda: self._move_relative('backward'))
        btn_l = QPushButton("Left"); btn_l.clicked.connect(lambda: self._move_relative('left'))
        btn_r = QPushButton("Right"); btn_r.clicked.connect(lambda: self._move_relative('right'))
        btn_u = QPushButton("Up"); btn_u.clicked.connect(lambda: self._move_relative('up'))
        btn_d = QPushButton("Down"); btn_d.clicked.connect(lambda: self._move_relative('down'))

        rel_layout.addWidget(btn_fwd, 0, 1)
        rel_layout.addWidget(btn_bwd, 2, 1)
        rel_layout.addWidget(btn_l, 1, 0)
        rel_layout.addWidget(btn_r, 1, 2)
        rel_layout.addWidget(btn_u, 0, 2)
        rel_layout.addWidget(btn_d, 2, 2)

        panel_layout.addWidget(abs_group)
        panel_layout.addWidget(rel_group)
        panel_layout.addStretch(1)
        return panel

    def _apply_absolute_camera_pose(self):
        """스핀박스와 콤보박스의 값으로 카메라의 절대 포즈를 설정합니다."""
        pos = np.array([self.dx_spin.value(), self.dy_spin.value(), self.dz_spin.value()])
        rot_degs = [self.rx_spin.value(), self.ry_spin.value(), self.rz_spin.value()]
        order = self.rot_order_combo.currentText()

        try:
            # Camera-to-World (c2w) 행렬 생성
            c2w = np.eye(4)
            c2w[:3, :3] = R.from_euler(order, rot_degs, degrees=True).as_matrix()
            c2w[:3, 3] = pos
            
            # View 행렬 (World-to-Camera)은 c2w의 역행렬
            view_matrix = np.linalg.inv(c2w)
            
            self.viewer.camera.Set_view_mat(view_matrix.astype(np.float32))
            self.viewer.update()
        except Exception as e:
            print(f"Error applying camera pose: {e}")

    def _move_relative(self, direction: str):
        """현재 카메라 시점을 기준으로 이동합니다."""
        cam = self.viewer.camera
        step = self.move_step
        
        if direction == 'forward':   cam.Zoom(1, sensitivity=step)
        elif direction == 'backward':cam.Zoom(-1, sensitivity=step)
        elif direction == 'left':    cam.Pan(10, 0, sensitivity=step*0.05)
        elif direction == 'right':   cam.Pan(-10, 0, sensitivity=step*0.05)
        elif direction == 'up':      cam.Pan(0, 10, sensitivity=step*0.05)
        elif direction == 'down':    cam.Pan(0, -10, sensitivity=step*0.05)
        
        self.viewer.update()

    def on_viewer_ready(self):
        """ViewerWidget 초기화가 완료된 후 호출되는 슬롯."""
        print("Viewer is initialized and ready.")
        axis_mesh = o3d.geometry.TriangleMesh.create_coordinate_frame(
            size=0.5, origin=[0, 0, 0])

        self.viewer.add_asset({
            "axis": Resource(
                obj_type=Obj_Type.TRAJ,
                data=axis_mesh
            )
        })
        self._apply_absolute_camera_pose() # 초기 카메라 위치 적용

    def add_random_gaussians(self):
        """'Add Random 3DGS' 버튼 클릭 시 호출되는 슬롯."""
        self.random_dgs_count += 1
        new_name = f"random_dgs_{self.random_dgs_count}"
        print(f"Adding new asset: {new_name}")

        random_gaussians = Create_random_3DGS(num_points=2000)
        self.viewer.add_asset({
            new_name: Resource(
                obj_type=Obj_Type.GAUSSIAN_SPLAT,
                data=random_gaussians
            )
        })

    def Run(self):
        """애플리케이션 실행 시 호출됩니다."""
        print("Render_Example_Window is running.")
        print(" - Mouse Left Button + Drag: Rotate Camera")
        print(" - Mouse Right Button + Drag: Pan Camera")
        print(" - Mouse Wheel: Zoom In/Out")

    def Stop(self):
        """애플리케이션 종료 시 호출됩니다."""
        print("Render_Example_Window is stopping.")


def main():
    """
    애플리케이션을 시작하는 메인 함수.
    """
    starter = Application_Starter()
    main_window = Render_Example_Window(
        title="Renderer Example with Camera Controls",
        position=(100, 100, 1600, 900) # 윈도우 크기 조정
    )
    starter.Start(main_window)


if __name__ == "__main__":
    main()
