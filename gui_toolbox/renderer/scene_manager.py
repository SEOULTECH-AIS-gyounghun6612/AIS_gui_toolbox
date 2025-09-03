"""렌더링 대상이 되는 Scene과 View Camera를 관리하는 모듈."""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from vision_toolbox.asset import (
    Scene,
    Gaussian_3DGS,
    Point_Cloud
)

from .render import OpenGL_Renderer
from .definitions import Resource, Obj_Type, Sorter_Type, Render_Opt, Clear_Opt
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
            clear_mask=Clear_Opt.COLOR | Clear_Opt.DEPTH,
            sorter_type=Sorter_Type.OPENGL
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

    def Render_scene(self):
        """현재 씬을 렌더링합니다."""
        self.renderer.Render(self.view_cam)

    def Fit_camera_to_scene(self):
        """현재 씬의 모든 에셋에 맞춰 카메라를 조정합니다."""
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