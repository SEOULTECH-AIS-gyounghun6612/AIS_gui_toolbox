from __future__ import annotations
from typing import Any, Literal
from dataclasses import InitVar, dataclass, field

from numpy import ndarray, arctan2, array, stack

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


class Draw():
    @staticmethod
    def Camera(
        viser_server: viser.ViserServer,
        name: str,
        img: ndarray,
        focal_length: float,
        scale: float = 0.3,
        line_width: float = 2.0,
        color: tuple[int, int, int] = (0, 255, 0),
        wxyz: tuple[float, float, float, float] = (1, 0, 0, 0),
        position: tuple[float, float, float] = (0, 0, 0),
        visible: bool = True
    ):
        _h, _w = img.shape[:2]
        _fov = 2 * arctan2(_h / 2, focal_length)
        return viser_server.scene.add_camera_frustum(
            name, _fov, _w / _h, scale, line_width, color,
            wxyz=wxyz, position=position, visible=visible
        )

    @staticmethod
    def Frame(
        viser_server: viser.ViserServer,
        name: str,
        color: tuple[int, int, int],
        show_axes: bool = True,
        axes_length: float = 0.5,
        axes_radius: float = 0.025,
        origin_radius: float | None = None,
        wxyz: tuple[float, float, float, float] = (1, 0, 0, 0),
        position: tuple[float, float, float] = (0, 0, 0),
        visible: bool = True,
    ):
        return viser_server.scene.add_frame(
            name, show_axes, axes_length, axes_radius, origin_radius,
            origin_color=color, wxyz=wxyz, position=position, visible=visible
        )

    @staticmethod
    def Line(
        viser_server: viser.ViserServer,
        name: str,
        points: ndarray | list,
        color: ndarray | tuple[int, int, int],
        line_width: int = 1,
        wxyz: tuple[float, float, float, float] = (1, 0, 0, 0),
        position: tuple[float, float, float] = (0, 0, 0),
        visible: bool = True
    ):
        _points = points if isinstance(points, ndarray) else array(points)
        _points = stack((_points[:-1], _points[1:]), axis=1)
        return viser_server.scene.add_line_segments(
            name, _points, color, line_width,
            wxyz=wxyz, position=position, visible=visible
        )

    @staticmethod
    def Point_cloud(
        viser_server: viser.ViserServer,
        name: str,
        points: ndarray,
        color: ndarray | tuple[int, int, int],
        point_size: float = 0.1,
        point_shape: Literal[
            'square', 'diamond', 'circle', 'rounded', 'sparkle'] = "rounded",
        wxyz: tuple[float, float, float, float] = (1, 0, 0, 0),
        position: tuple[float, float, float] = (0, 0, 0),
        visible: bool = True,
    ):
        return viser_server.scene.add_point_cloud(
            name, points, color, point_size, point_shape,
            wxyz=wxyz, position=position, visible=visible
        )


class Server(QThread):
    def __init__(
        self,
        interface_cfg: Interface_Config,
        host: str = "127.0.0.1", port: int = 8080,
        parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self.server = viser.ViserServer(host, port)

        self.ui = {}

        self.display_data: dict[str, Any] = {}

        self.is_active = True

        self._Set_ui(self.server, interface_cfg, self.ui)
        self.Set_event()

    def _Set_ui(
        self,
        server: viser.ViserServer,
        cfg: Interface_Config,
        element_holder: dict[str, Any]
    ):
        _name = cfg.name

        if isinstance(cfg.contents_cfg, list):
            # is folder
            for _cfg in cfg.contents_cfg:
                if _cfg.element_type == "folder":
                    with server.gui.add_folder(_cfg.name):
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

    def Get_http_address(self):
        _server = self.server
        return QUrl(f"http://{_server.get_host()}:{_server.get_port()}")
