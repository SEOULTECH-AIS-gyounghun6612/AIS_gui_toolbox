"""
gui_toolbox 렌더러 사용법을 보여주는 메인 예제 스크립트.

이 스크립트는 PySide6 애플리케이션을 설정하고,
3D 렌더링을 위한 ViewerWidget을 포함하는 메인 윈도우를 생성합니다.
"""

import open3d as o3d
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout

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
    OpenGL 뷰어 위젯과 컨트롤 버튼을 포함하는 메인 윈도우 클래스.
    """
    def __Initialize_data__(self, **kwarg):
        """데이터 관련 초기화. 무작위 객체 이름 생성을 위한 카운터 설정."""
        self.random_dgs_count = 0

    def __Initialize_interface__(self, **kwarg):
        """
        UI 초기화. ViewerWidget과 버튼을 생성하고 레이아웃에 배치합니다.
        """
        # --- 위젯 생성 ---
        self.viewer = ViewerWidget(parent=self, sorter_type=Sorter_Type.OPENGL)
        self.add_random_button = QPushButton("Add Random 3DGS")

        # --- 레이아웃 설정 ---
        layout = QVBoxLayout()
        layout.addWidget(self.viewer)
        layout.addWidget(self.add_random_button)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # --- 시그널-슬롯 연결 ---
        self.add_random_button.clicked.connect(self.add_random_gaussians)
        self.viewer.initialized.connect(self.on_viewer_ready)

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
        print(" - Click 'Add Random 3DGS' button to add more objects.")

    def Stop(self):
        """애플리케이션 종료 시 호출됩니다."""
        print("Render_Example_Window is stopping.")
        self.viewer.cleanup()


def main():
    """
    애플리케이션을 시작하는 메인 함수.
    """
    starter = Application_Starter()
    main_window = Render_Example_Window(
        title="Renderer Example",
        position=(100, 100, 1280, 720)
    )
    starter.Start(main_window)


if __name__ == "__main__":
    main()
