"""렌더링 대상이 되는 Scene과 View Camera를 관리하는 모듈."""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import open3d as o3d
import open3d.geometry as o3d_geo

from vision_toolbox.asset import (
    Scene,
    Gaussian_3DGS,
    Point_Cloud
)

from .render import OpenGL_Renderer
from .definitions import Resource, Obj_Type, Render_Opt, Clear_Opt
from .view_camera import View_Cam


@dataclass
class Scene_Manager:
    """렌더링할 Scene과 View_Cam, Renderer를 모두 관리하는 클래스."""
    scene: Scene
    view_cam: View_Cam
    renderer: OpenGL_Renderer

    @classmethod
    def From_default(cls, width: int, height: int) -> Scene_Manager:
        """기본값으로 Scene_Manager 객체를 생성합니다."""
        _scene = Scene(name="default_scene")
        _view_cam = View_Cam.Create_at_origin(width, height)
        _opts = (
            Render_Opt.DEPTH, Render_Opt.BLEND,
            Render_Opt.MULTISAMPLE_AA, Render_Opt.P_ABLE_P_SIZE
        )
        _renderer = OpenGL_Renderer(
            bg_color=(0.5, 0.5, 0.5, 1.0),
            enable_opts=_opts,
            clear_mask=Clear_Opt.COLOR | Clear_Opt.DEPTH
        )
        return cls(scene=_scene, view_cam=_view_cam, renderer=_renderer)

    def Initialize_renderer(self):
        """렌더러를 초기화합니다."""
        self.renderer.Initialize()

    def Set_scene(self, scene: Scene):
        """새로운 씬을 설정하고 렌더링을 준비합니다."""
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

    def Add_axis(
        self, name: str, size: float = 1.0, 
        pose: np.ndarray = np.eye(4, dtype=np.float32)
    ):
        """디버깅을 위해 XYZ 좌표축(R,G,B)을 렌더링 목록에 추가합니다."""
        # X-axis (Red)
        ls_x = o3d_geo.LineSet(
            points=o3d.utility.Vector3dVector([[0,0,0], [size,0,0]]),
            lines=o3d.utility.Vector2iVector([[0,1]])
        )
        res_x = Resource(obj_type=Obj_Type.TRAJ, data=ls_x, pose=pose, color_opt=(1,0,0))

        # Y-axis (Green)
        ls_y = o3d_geo.LineSet(
            points=o3d.utility.Vector3dVector([[0,0,0], [0,size,0]]),
            lines=o3d.utility.Vector2iVector([[0,1]])
        )
        res_y = Resource(obj_type=Obj_Type.TRAJ, data=ls_y, pose=pose, color_opt=(0,1,0))

        # Z-axis (Blue)
        ls_z = o3d_geo.LineSet(
            points=o3d.utility.Vector3dVector([[0,0,0], [0,0,size]]),
            lines=o3d.utility.Vector2iVector([[0,1]])
        )
        res_z = Resource(obj_type=Obj_Type.TRAJ, data=ls_z, pose=pose, color_opt=(0,0,1))

        self.renderer.Add_or_update_resources({
            f"{name}_x": res_x,
            f"{name}_y": res_y,
            f"{name}_z": res_z,
        })

    def Add_trajectory(
        self,
        name: str,
        color: tuple[float, float, float] = (1.0, 0.0, 0.0)
    ):
        """
        씬에 있는 카메라들의 위치를 수집하여 궤적(LineSet)을 생성하고
        렌더링 목록에 추가합니다. 카메라는 이름순으로 정렬됩니다.
        """
        if not self.scene or not self.scene.cameras:
            return

        # Collect camera positions
        points = np.array(
            [cam.pose[:3, 3] for _, cam in self.scene.cameras.items()]
        )

        if len(points) < 2:
            return

        # Create LineSet geometry
        line_set = o3d_geo.LineSet(
            points=o3d.utility.Vector3dVector(points.astype(np.float64)),
            lines=o3d.utility.Vector2iVector(
                [[i, i + 1] for i in range(len(points) - 1)]
            ),
        )

        # Create a resource with TRAJ type and color option
        resource = Resource(
            obj_type=Obj_Type.TRAJ,
            data=line_set,
            pose=np.eye(4, dtype=np.float32),  # World coordinates
            color_opt=color
        )
        self.renderer.Add_or_update_resources({name: resource})

    def Render_scene(self):
        """현재 씬을 렌더링합니다."""
        self.renderer.Render(self.view_cam)

    def Fit_camera_to_scene(self):
        """현재 씬의 모든 에셋에 맞춰 카메라를 조정합니다."""
        all_points = []
        for asset in self.scene.assets.values():
            if hasattr(asset, 'points') and asset.points.size > 0:
                all_points.append(asset.points)
        
        # Also consider camera positions for fitting
        if self.scene.cameras:
            cam_points = np.array([c.pose[:3, 3] for c in self.scene.cameras.values()])
            if cam_points.size > 0:
                all_points.append(cam_points)

        if not all_points:
            return

        combined_points = np.vstack(all_points)
        _min_bound = combined_points.min(axis=0)
        _max_bound = combined_points.max(axis=0)

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