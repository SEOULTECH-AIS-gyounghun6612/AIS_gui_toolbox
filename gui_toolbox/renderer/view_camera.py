"""렌더링 시점(Viewpoint)을 제어하는 인터랙티브 카메라 클래스."""

from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from scipy.spatial.transform import Rotation

from vision_toolbox.asset import Camera as CameraData


@dataclass
class View_Cam:
    """마우스 입력으로 조작 가능한 FPS 스타일 인터랙티브 카메라."""
    cam_data: CameraData
    
    yaw: float = field(init=False, default=-90.0)
    pitch: float = field(init=False, default=0.0)

    near_plane: float = 0.01
    far_plane: float = 100.0

    view_mat: np.ndarray = field(init=False)
    proj_mat: np.ndarray = field(init=False)

    def __post_init__(self):
        """cam_data의 pose로부터 모든 파생 속성을 초기화합니다."""
        self._Update_derived_props_from_pose()
        self._Update_proj_matrix()

    @classmethod
    def Create_at_origin(cls, width: int, height: int) -> View_Cam:
        """원점에서 기본 설정으로 View_Cam 객체를 생성합니다."""
        _cam_data = CameraData(
            name="default_cam",
            pose=np.eye(4, dtype=np.float32),
            intrinsics=np.array(
                [[1100, 0, width/2], [0, 1100, height/2], [0, 0, 1]], 
                dtype=np.float32
            ),
            image_size=np.array([width, height])
        )
        _cam_data.pose[2, 3] = 5.0
        return cls(cam_data=_cam_data)

    def _Update_derived_props_from_pose(self):
        """C2W 포즈 행렬로부터 Yaw, Pitch, View Matrix를 역산합니다."""
        self.view_mat = np.linalg.inv(self.cam_data.pose)
        _front = -self.cam_data.pose[:3, 2]
        self.pitch = np.clip(np.degrees(np.arcsin(_front[1])), -89.0, 89.0)
        self.yaw = np.degrees(np.arctan2(_front[2], _front[0]))

    def _Update_proj_matrix(self):
        """카메라 내부 파라미터로부터 투영 행렬을 생성합니다."""
        _fx, _fy = self.cam_data.intrinsics[0, 0], self.cam_data.intrinsics[1, 1]
        _cx, _cy = self.cam_data.intrinsics[0, 2], self.cam_data.intrinsics[1, 2]
        _w, _h = self.cam_data.image_size
        
        self.proj_mat = np.zeros((4, 4), dtype=np.float32)
        self.proj_mat[0, 0] = 2 * _fx / _w
        self.proj_mat[1, 1] = 2 * _fy / _h
        self.proj_mat[0, 2] = -(2 * _cx / _w - 1)
        self.proj_mat[1, 2] = -(2 * _cy / _h - 1)
        _z_sum = self.far_plane + self.near_plane
        _z_diff = self.far_plane - self.near_plane
        self.proj_mat[2, 2] = -_z_sum / _z_diff
        self.proj_mat[2, 3] = -2 * self.far_plane * self.near_plane / _z_diff
        self.proj_mat[3, 2] = -1.0

    def Rotate(self, dx: float, dy: float, sensitivity: float = 0.1):
        """쿼터니언 기반으로 카메라를 회전시킵니다."""
        _current_rot = Rotation.from_matrix(self.cam_data.pose[:3, :3])
        _yaw_rot = Rotation.from_rotvec(dx * sensitivity * np.array([0, -1, 0]), degrees=True)
        _pitch_rot = Rotation.from_rotvec(dy * sensitivity * np.array([1, 0, 0]), degrees=True)

        _new_rot = _yaw_rot * _current_rot * _pitch_rot
        self.cam_data.pose[:3, :3] = _new_rot.as_matrix()
        self._Update_derived_props_from_pose()

    def Move(self, forward: float, right: float, up: float, sensitivity: float = 0.1):
        """카메라 위치를 이동시킵니다."""
        _c2w = self.cam_data.pose
        _pos = _c2w[:3, 3]
        _pos += -_c2w[:3, 2] * forward * sensitivity
        _pos += _c2w[:3, 0] * right * sensitivity
        _pos += _c2w[:3, 1] * up * sensitivity
        self.cam_data.pose[:3, 3] = _pos
        self._Update_derived_props_from_pose()

    def Set_projection(self, width: int, height: int):
        """화면 크기 변경에 따라 투영 행렬을 업데이트합니다."""
        self.cam_data.image_size = np.array([width, height])
        self._Update_proj_matrix()