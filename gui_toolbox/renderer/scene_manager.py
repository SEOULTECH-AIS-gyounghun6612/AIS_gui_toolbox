"""렌더링 대상이 되는 Scene과 View Camera를 관리하는 모듈."""

from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from scipy.spatial.transform import Rotation

from vision_toolbox.asset import (
    Scene,
    Camera as CameraData,
    Gaussian_3DGS,
    Point_Cloud
)

from .render import OpenGL_Renderer
from .definitions import Resource, Obj_Type, Sorter_Type, Render_Opt, Clear_Opt


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
        self._Update_derived_props_from_pose()
        self._Update_proj_matrix()

    @classmethod
    def Create_at_origin(cls, width: int, height: int) -> View_Cam:
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
        self.view_mat = np.linalg.inv(self.cam_data.pose)
        _front = -self.cam_data.pose[:3, 2]
        self.pitch = np.clip(np.degrees(np.arcsin(_front[1])), -89.0, 89.0)
        self.yaw = np.degrees(np.arctan2(_front[2], _front[0]))

    def _Update_proj_matrix(self):
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
        # 1. 현재 회전을 쿼터니언으로 변환
        _current_rot = Rotation.from_matrix(self.cam_data.pose[:3, :3])

        # 2. 마우스 움직임에 따른 yaw, pitch 변화량 쿼터니언 생성
        _yaw_rot = Rotation.from_rotvec(dx * sensitivity * np.array([0, -1, 0]), degrees=True)
        _pitch_rot = Rotation.from_rotvec(dy * sensitivity * np.array([1, 0, 0]), degrees=True)

        # 3. 회전 결합: Yaw는 월드 Y축 기준, Pitch는 카메라 로컬 X축 기준
        _new_rot = _yaw_rot * _current_rot * _pitch_rot
        self.cam_data.pose[:3, :3] = _new_rot.as_matrix()

        # 4. 파생 속성 업데이트
        self._Update_derived_props_from_pose()

    def Move(self, forward: float, right: float, up: float, sensitivity: float = 0.1):
        _c2w = self.cam_data.pose
        _pos = _c2w[:3, 3]
        _pos += -_c2w[:3, 2] * forward * sensitivity
        _pos += _c2w[:3, 0] * right * sensitivity
        _pos += _c2w[:3, 1] * up * sensitivity
        self.cam_data.pose[:3, 3] = _pos
        self._Update_derived_props_from_pose()

    def Set_projection(self, width: int, height: int):
        self.cam_data.image_size = np.array([width, height])
        self._Update_proj_matrix()


@dataclass
class Scene_Manager:
    """렌더링할 Scene과 View_Cam, Renderer를 모두 관리하는 클래스."""
    scene: Scene
    view_cam: View_Cam
    renderer: OpenGL_Renderer

    @classmethod
    def From_default(cls, width: int, height: int) -> Scene_Manager:
        _scene = Scene(name="default_scene")
        _view_cam = View_Cam.Create_at_origin(width, height)
        _opts = (
            Render_Opt.DEPTH, Render_Opt.BLEND,
            Render_Opt.MULTISAMPLE_AA, Render_Opt.P_ABLE_P_SIZE
        )
        _renderer = OpenGL_Renderer(
            bg_color=(0.5, 0.5, 0.5, 1.0),
            enable_opts=_opts,
            clear_mask=Clear_Opt.COLOR | Clear_Opt.DEPTH,
            sorter_type=Sorter_Type.OPENGL
        )
        return cls(scene=_scene, view_cam=_view_cam, renderer=_renderer)

    def Initialize_renderer(self):
        self.renderer.Initialize()

    def Set_scene(self, scene: Scene):
        self.scene = scene
        self.Fit_camera_to_scene()
        _resources = {}
        for _name, _asset in scene.assets.items():
            if isinstance(_asset, Gaussian_3DGS):
                _obj_type = Obj_Type.GAUSSIAN_SPLAT
            elif isinstance(_asset, Point_Cloud):
                _obj_type = Obj_Type.POINTS
            else:
                continue
            _resources[_name] = Resource(obj_type=_obj_type, data=_asset)
        
        _current_assets = list(self.renderer.render_objects.keys())
        self.renderer.Remove_resources(_current_assets)
        self.renderer.Add_or_update_resources(_resources)

    def Render_scene(self):
        self.renderer.Render(self.view_cam)

    def Fit_camera_to_scene(self):
        _min_bound = np.array([np.inf, np.inf, np.inf])
        _max_bound = np.array([-np.inf, -np.inf, -np.inf])
        _has_points = False
        for _asset in self.scene.assets.values():
            if hasattr(_asset, 'points') and _asset.points.size > 0:
                _has_points = True
                _min_bound = np.minimum(_min_bound, _asset.points.min(axis=0))
                _max_bound = np.maximum(_max_bound, _asset.points.max(axis=0))

        if not _has_points: return

        _center = (_min_bound + _max_bound) / 2.0
        _size = np.linalg.norm(_max_bound - _min_bound)
        if _size < 1e-6: return

        _fx = self.view_cam.cam_data.intrinsics[0, 0]
        _fy = self.view_cam.cam_data.intrinsics[1, 1]
        _w, _h = self.view_cam.cam_data.image_size
        _fov_x = 2 * np.arctan(_w / (2 * _fx))
        _fov_y = 2 * np.arctan(_h / (2 * _fy))
        _fov = min(_fov_x, _fov_y)
        
        _distance = (_size / 2.0) / np.tan(_fov / 2.0)
        _new_pos = _center + np.array([0, 0, _distance * 1.5])
        
        _z_axis = _center - _new_pos
        _z_axis /= np.linalg.norm(_z_axis)
        _x_axis = np.cross(np.array([0., 1., 0.]), _z_axis)
        _x_axis /= np.linalg.norm(_x_axis)
        _y_axis = np.cross(_z_axis, _x_axis)

        _new_pose = np.eye(4)
        _new_pose[:3, 0] = _x_axis
        _new_pose[:3, 1] = _y_axis
        _new_pose[:3, 2] = _z_axis
        _new_pose[:3, 3] = _new_pos
        self.view_cam.cam_data.pose = _new_pose
        self.view_cam._Update_derived_props_from_pose()