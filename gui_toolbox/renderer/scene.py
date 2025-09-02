from dataclasses import dataclass, field

import numpy as np

from vision_toolbox.utils.vision_types import TP_M
from vision_toolbox.asset import (
    Image, Point_Cloud, Gaussian_3D,
    Camera
)

@dataclass
class Base_Frame:
    """
    특정 프레임의 데이터 연결 정보(인덱스)를 담는 중간 컨테이너.
    이곳에 V-SLAM, NeRF 등 프레임 단위 처리 알고리즘을 위한 메서드 추가 가능.
    """
    # 촬영에 사용된 카메라 포즈의 인덱스
    cam_id: int
    cam_pose_id: int

    # 이 View에 포함된 2D/3D 객체와, 해당 객체의 포즈 인덱스를 매핑
    # key: Scene에 등록된 3D 객체의 고유 ID
    # value: Scene의 object_poses 배열 내의 인덱스
    obj_ids: dict[int, int] = field(default_factory=dict)

    # 이 View에 해당하는 이미지 Asset의 ID
    rgb_id: int | None = None
    depth_id: int | None = None

    # ToDo: 추가 2d 이미지 데이터를 사용하는 경우 아래에 추가


@dataclass
class Scene:
    """모든 Asset과 Pose 데이터를 소유하고, View를 통해 장면을 구성."""
    name: str

    # --- 데이터 저장소 (Data Storages) ---

    # 3D 객체 에셋 저장소 (고유 ID -> Asset)
    assets_3d: dict[int, Gaussian_3D | Point_Cloud] = field(default_factory=dict)

    # 2D 이미지 에셋 저장소 (고유 ID -> Asset)
    assets_2d: dict[int, Image] = field(default_factory=dict)

    # 카메라 에셋 저장소 (Asset)
    cams: Camera = field(default_factory=Camera)
    # 모든 카메라 포즈를 담는 단일 배열
    cam_poses: TP_M = field(
        default_factory=lambda: np.empty((0, 4, 4), dtype=np.float32)
    )

    # 모든 3D 객체 포즈를 담는 단일 배열
    object_poses: TP_M = field(
        default_factory=lambda: np.empty((0, 4, 4), dtype=np.float32)
    )

    # --- 논리적 구조 (Logical Structure) ---

    # 프레임 번호와 View를 매핑하여 시간의 흐름을 정의
    tracks: dict[int, Base_Frame] = field(default_factory=dict)


@dataclass
class View_Cam:
    """마우스 입력으로 조작 가능한 아크볼 스타일 카메라 (Dataclass 버전)"""
    # --- 초기화 시 설정되는 인자 ---
    width: int
    height: int
    target: np.ndarray = field(default_factory=lambda: np.array([0., 0., 0.]))

    # --- 기본값을 가지는 카메라 상태 변수 ---
    up: np.ndarray = field(default_factory=lambda: np.array([0., 1., 0.]))
    radius: float = 5.0  # Zoom
    theta: float = np.radians(45.0)  # 수평 회전 (Azimuth)
    phi: float = np.radians(60.0)    # 수직 회전 (Elevation)

    # [개선] fov는 수평(x) 화각을 의미하도록 명확화
    fov_x_rad: float = np.radians(90.0)
    near_plane: float = 0.1
    far_plane: float = 100.0

    # --- __post_init__ 에서 계산되는 필드 ---
    position: np.ndarray = field(init=False)
    view_mat: np.ndarray = field(init=False)
    proj_matrix: np.ndarray = field(init=False)
    c2w_mat: np.ndarray = field(init=False)
    fov_y_rad: float = field(init=False)

    def __post_init__(self):
        """Dataclass 초기화 후 실행되는 메서드"""
        _ratio = self.width / self.height if self.height > 0 else 1.0
        _tan_fov_x_half = np.tan(self.fov_x_rad / 2.0)
        _tan_fov_y_half = _tan_fov_x_half / _ratio
        self.fov_y_rad = 2 * np.arctan(_tan_fov_y_half)

        self.__Update_view_mat()
        self.Set_projection(self.width, self.height)

    def __Update_view_mat(self):
        """구면 좌표계로부터 카메라 위치를 계산하고 행렬들을 갱신"""
        _trg, _r, _p, _th = self.target, self.radius, self.phi, self.theta
        _eye_x = _trg[0] + _r * np.sin(_p) * np.cos(_th)
        _eye_y = _trg[1] + _r * np.cos(_p)
        _eye_z = _trg[2] + _r * np.sin(_p) * np.sin(_th)
        eye = np.array([_eye_x, _eye_y, _eye_z])

        self.position, self.c2w_mat, self.view_mat = self.__Look_at(
            eye, _trg, self.up
        )

    def __Look_at(self, eye, target, up):
        _z = eye - target
        if np.linalg.norm(_z) > 1e-6:
            _z /= np.linalg.norm(_z)
        _x = np.cross(up, _z)
        if np.linalg.norm(_x) > 1e-6:
            _x /= np.linalg.norm(_x)
        _y = np.cross(_z, _x)

        _c2w = np.identity(4, dtype=np.float32)
        _c2w[:3, 0], _c2w[:3, 1], _c2w[:3, 2], _c2w[:3, 3] = _x, _y, _z, eye
        return eye, _c2w, np.linalg.inv(_c2w)

    def __Perspective(self, fov_y, aspect, z_near, z_far) -> np.ndarray:
        _mat = np.zeros((4, 4), dtype=np.float32)
        _f = 1.0 / np.tan(fov_y / 2.0)
        _mat[0, 0] = _f / aspect
        _mat[1, 1] = _f
        _mat[2, 2] = (z_far + z_near) / (z_near - z_far)
        _mat[2, 3] = (2.0 * z_far * z_near) / (z_near - z_far)
        _mat[3, 2] = -1.0
        return _mat.T

    # --- Public Methods ---
    def Tilt(self, dx: float, dy: float, sensitivity: float = 0.01):
        self.theta += dx * sensitivity
        self.phi = np.clip(self.phi + dy * sensitivity, 0.01, np.pi - 0.01)
        self.__Update_view_mat()

    def Pan(self, dx: float, dy: float, sensitivity: float = 0.01):
        """[복구 및 최적화] 카메라의 로컬 축을 기준으로 target 위치를 평행 이동"""
        _r = self.c2w_mat[:3, 0]
        _u = self.c2w_mat[:3, 1]

        self.target -= _r * dx * sensitivity
        self.target += _u * dy * sensitivity
        self.__Update_view_mat()

    def Zoom(self, delta: float, sensitivity: float = 0.1):
        self.radius -= delta * sensitivity
        self.radius = max(self.radius, 0.1)
        self.__Update_view_mat()

    def Set_view_mat(self, view_mat: TP_M):
        self.view_mat = view_mat
        _c2w = np.linalg.inv(view_mat)
        self.c2w_mat = _c2w
        self.position = _c2w[:3, 3]

    def Set_projection(self, width: int, height: int):
        self.width, self.height = width, height
        if self.height == 0:
            return

        _ratio = self.width / self.height
        self.proj_matrix = self.__Perspective(
            self.fov_y_rad, _ratio, self.near_plane, self.far_plane
        )

    def Get_hfovxy_focal(self) -> np.ndarray:
        """수평/수직 FoV를 바탕으로 픽셀 단위 초점 거리 (fx, fy)를 계산"""
        return np.array([
            (self.width / 2.0) / np.tan(self.fov_x_rad / 2.0),
            (self.height / 2.0) / np.tan(self.fov_y_rad / 2.0),
            0.0
        ], dtype=np.float32)


# for Debug
def Create_dummy_3DGS(
    num_points=5000, file_name="test_dummy_3DGS.ply"
) -> Gaussian_3D:
    print(f"Creating {num_points} dummy Gaussian splats...")
    # 원환(torus) 모양의 포인트 생성
    radius_torus, radius_tube = 1.5, 1.0
    _u = np.random.rand(num_points) * 2 * np.pi
    _v = np.random.rand(num_points) * 2 * np.pi
    _x = (radius_torus + radius_tube * np.cos(_v)) * np.cos(_u)
    _y = (radius_torus + radius_tube * np.cos(_v)) * np.sin(_u)
    _z = radius_tube * np.sin(_v)

    _pts = np.vstack([_x, _y, _z]).T.astype(np.float32)
    _colors = np.random.rand(num_points, 3).astype(np.float32)
    _a = np.random.uniform(0.5, 1.0, (num_points, 1)).astype(np.float32)
    _s = np.random.uniform(0.01, 0.03, (num_points, 3)).astype(np.float32)

    # 정규화된 쿼터니언 (기본 회전 없음)
    _rot = np.zeros((num_points, 4), dtype=np.float32)
    _rot[:, 3] = 1.0

    return Gaussian_3D(
        relative_path=file_name,
        points=_pts,
        opacities=_a,
        scales=_s,
        rotations=_rot,
        colors=_colors
    )


def Create_axis_3DGS(file_name="test_axis_3DGS.ply") -> Gaussian_3D:
    """
    테스트와 동일한 데이터를 생성하여 Gaussian_3D 객체를 반환합니다.
    """
    _xyz = np.array([
        [0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]
    ], dtype=np.float32)

    _rot = np.array([
        [0, 0, 0, 1], [0, 0, 0, 1], [0, 0, 0, 1], [0, 0, 0, 1]
    ], dtype=np.float32)

    _s = np.array([
        [0.03, 0.03, 0.03], [0.2, 0.03, 0.03],
        [0.03, 0.2, 0.03], [0.03, 0.03, 0.2]
    ], dtype=np.float32)

    _a = np.array([[1], [1], [1], [1]], dtype=np.float32)

    # 기본 RGB 색상 정의 (SH 0차 계수로 사용될 값)
    _c_rgb = np.array([
        [1, 0, 1], [1, 0, 0], [0, 1, 0], [0, 0, 1]
    ], dtype=np.float32)

    # 셰이더 활성화 함수의 역연산을 적용하여 SH 0차 계수(DC) 생성
    C0 = 0.28209479177387814
    sh_dc = (_c_rgb - 0.5) / C0

    # colors 필드(N, 48) 형태에 맞게 나머지 SH 계수(AC)를 0으로 채움
    _num_pts = _xyz.shape[0]
    _sh_padding = np.zeros((_num_pts, 45), dtype=np.float32)
    _sh_features = np.concatenate([sh_dc, _sh_padding], axis=1)

    return Gaussian_3D(
        relative_path=file_name,
        points=_xyz,
        rotations=_rot,
        scales=_s,
        opacities=_a,
        colors=_sh_features
    )

def Create_random_3DGS(
    num_points=1000,
    center: np.ndarray = np.array([0.0, 0.0, 0.0]),
    radius: float = 1.0,
    file_name="random_dummy_3DGS.ply"
) -> Gaussian_3D:
    """구(sphere) 안에 무작위로 흩뿌려진 3DGS 객체를 생성합니다."""
    print(f"Creating {num_points} random Gaussian splats...")

    # 구 안에 균일하게 분포된 무작위 포인트 생성
    phi = np.random.uniform(0, 2 * np.pi, num_points)
    costheta = np.random.uniform(-1, 1, num_points)
    u = np.random.uniform(0, 1, num_points)

    theta = np.arccos(costheta)
    r = radius * np.cbrt(u)

    _x = r * np.sin(theta) * np.cos(phi) + center[0]
    _y = r * np.sin(theta) * np.sin(phi) + center[1]
    _z = r * np.cos(theta) + center[2]

    _pts = np.vstack([_x, _y, _z]).T.astype(np.float32)
    _colors = np.random.rand(num_points, 3).astype(np.float32)
    _a = np.random.uniform(0.7, 1.0, (num_points, 1)).astype(np.float32)
    _s = np.random.uniform(0.01, 0.05, (num_points, 3)).astype(np.float32)

    # 정규화된 쿼터니언 (기본 회전 없음)
    _rot = np.zeros((num_points, 4), dtype=np.float32)
    _rot[:, 3] = 1.0

    return Gaussian_3D(
        relative_path=file_name,
        points=_pts,
        opacities=_a,
        scales=_s,
        rotations=_rot,
        colors=_colors
    )
