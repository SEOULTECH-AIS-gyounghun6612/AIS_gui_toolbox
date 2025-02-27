from __future__ import annotations
from typing import Any, Literal
from dataclasses import InitVar, dataclass, field

from numpy import ndarray, arctan2

from PySide6.QtCore import QObject, QThread, QUrl

import viser
from python_ex.project import Config


def l2t(data: list):
    return tuple(l2t(_d) if isinstance(_d, list) else _d for _d in data)


@dataclass
class Interface_Config(Config.Basement):
    contents: InitVar[dict[str, Any] | list[dict[str, Any]]]
    name: str
    element_type: Literal[
        "folder",
        "number", "text", "vector2", "vector3", "rgb",
        "slider", "multi_slider", "progress_bar",
        "upload_button", "button", "checkbox",
    ] | None
    contents_cfg: dict[str, Any] | list[Interface_Config] = field(init=False)

    def __post_init__(
        self, meta_con: dict[str, Any] | list[dict[str, Any]]
    ):
        self.contents_cfg = [
            Interface_Config(**_args) for _args in meta_con
        ] if isinstance(
            meta_con, list
        ) else dict((
            _k, l2t(_v) if isinstance(_v, list) else _v
        ) for _k, _v in meta_con.items())

    def Config_to_dict(self) -> dict[str, Any]:
        _con = self.contents_cfg
        return {
            "name": self.name,
            "element_type": self.element_type,
            "contents": [
                _i.Config_to_dict() for _i in _con
            ] if isinstance(_con, list) else _con
        }


class Server(QThread):
    @dataclass
    class Scene_Data(Config.Basement):
        name: str
        color: tuple[int, int, int]
        position: tuple[float, float, float] = (0, 0, 0)
        wxyz: tuple[float, float, float, float] = (1, 0, 0, 0)
        visible: bool = True

    def __init__(
        self,
        interface_cfg: Interface_Config,
        host: str = "127.0.0.1", port: int = 8080,
        parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self.server = viser.ViserServer(host, port)
        self.holder = {}

        self._Set_ui(self.server, interface_cfg, self.holder)
        self.Set_event()

    def _Set_ui(
        self,
        server: viser.ViserServer,
        cfg: Interface_Config,
        element_holder: dict[str, Any]
    ):
        _name = cfg.name

        if isinstance(cfg.contents_cfg, list):
            for _cfg in cfg.contents_cfg:
                if _cfg.element_type == "folder":
                    with server.gui.add_folder(_name):
                        self._Set_ui(server, _cfg, element_holder)
                else:
                    self._Set_ui(server, _cfg, element_holder)
        else:
            # viser에서 gui를 추가 하는 함수 -> add_{type}으로 구현됨
            _cmp = getattr(server.gui, f"add_{cfg.element_type}")(
                **cfg.contents_cfg,
                **({} if _name == "" else {"label": _name})
            )

            element_holder[f"{_name}_{cfg.element_type}"] = _cmp

    def Set_event(self):
        raise NotImplementedError

    def Add_cam(
        self,
        scene_info: Scene_Data,
        rgb_img: ndarray,
        focal_length: float,
        scale: float = 0.3,
    ):
        _h, _w = rgb_img.shape[:1]
        _arg = scene_info.Config_to_dict()
        _arg.update({
            "fov": 2 * arctan2(_h / 2, focal_length),
            "aspect": _w / _h,
            "scale": scale,
            "image": rgb_img
        })
        self.server.scene.add_camera_frustum(**_arg)

    def Add_frame(
        self,
        scene_info: Scene_Data,
        show_axes: bool = True,
        axes_length: float = 0.5,
        axes_radius: float = 0.025,
        origin_radius: float | None = None,
    ):
        _arg = scene_info.Config_to_dict()
        _arg.update({
            "show_axes": show_axes,
            "axes_length": axes_length,
            "axes_radius": axes_radius,
            "origin_radius": origin_radius
        })
        _arg["origin_color"] = _arg.pop("color")
        self.server.scene.add_frame(**_arg)

    def Add_line(
        self,
        scene_info: Scene_Data,
        points: ndarray,
        colors: ndarray | None = None,
        line_width: float = 1
    ):
        _arg = scene_info.Config_to_dict()

        _color = _arg.pop("color")
        _arg.update({
            "points": points,
            "colors": colors if colors is not None else _color,
            "line_width": line_width
        })

        self.server.scene.add_line_segments(**_arg)

    def Add_point_cloud(
        self,
        scene_info: Scene_Data,
        points: ndarray,
        colors: ndarray | None = None,
        point_size: float = 0.1,
        point_shape: Literal[
            'square', 'diamond', 'circle', 'rounded', 'sparkle'] = "rounded",
    ):
        _arg = scene_info.Config_to_dict()

        _color = _arg.pop("color")
        _arg.update({
            "points": points,
            "colors": colors if colors is not None else _color,
            "point_size": point_size,
            "point_shape": point_shape
        })

        self.server.scene.add_point_cloud(**_arg)

    def Get_http_address(self):
        _server = self.server
        return QUrl(f"http://{_server.get_host()}:{_server.get_port()}")
