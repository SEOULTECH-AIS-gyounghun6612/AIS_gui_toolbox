"""
gui_toolbox 렌더러 사용법을 보여주는 메인 예제 스크립트.

이 스크립트는 PySide6 애플리케이션을 설정하고,
리팩토링된 ViewerWidget을 사용하여 다양한 3D 에셋을 렌더링하는 방법을 보여줍니다.
"""
import sys
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow

from gui_toolbox.widget import ViewerWidget
from vision_toolbox.asset import Scene, Gaussian_3DGS, Point_Cloud


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


class Example_Window(QMainWindow):
    """ViewerWidget을 중앙에 배치하는 간단한 메인 윈도우."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GUI Toolbox - Refactored Renderer Example")
        self.setGeometry(100, 100, 1280, 720)

        self.viewer = ViewerWidget(parent=self)
        self.setCentralWidget(self.viewer)


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
    # ------------------------------------------

    # 위젯이 준비되면 Set_scene을 호출하도록 연결합니다.
    # GL 컨텍스트가 생성된 후에 호출되어야 합니다.
    window.viewer.initialized.connect(lambda: window.viewer.Set_scene(scene))
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
