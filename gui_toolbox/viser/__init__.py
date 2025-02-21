from __future__ import annotations
from typing import Any, Literal
from dataclasses import InitVar, dataclass, field

from PySide6.QtCore import QObject, QThread, QUrl

import viser
from gui_toolbox.widget import Interface_Config


@dataclass
class Action_Config(Interface_Config):
    i_contents: InitVar[dict[str, Any] | list[dict[str, Any]]]
    element_type: Literal[
        "folder",
        "number", "text", "vector2", "vector3", "rgb",
        "slider", "multi_slider", "progress_bar",
        "upload_button", "button", "checkbox",
    ] | None
    contents: dict[str, Any] | list[Action_Config] = field(
        default_factory=dict)

    def __post_init__(
        self, i_contents: dict[str, Any] | list[dict[str, Any]]
    ):
        def l2t(data: list):
            return tuple(
                l2t(_d) if isinstance(_d, list) else _d for _d in data)

        self.contents =  [
            Action_Config(**_args) for _args in i_contents
        ] if isinstance(
            i_contents, list
        ) else dict((
            _k, l2t(_v) if isinstance(_v, list) else _v
        ) for _k, _v in i_contents.items())


class Server(QThread):
    def __init__(
        self,
        cfg: Action_Config,
        host: str = "127.0.0.1", port: int = 8080,
        parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self.server = viser.ViserServer(host, port)
        self.holder = {}

        self._Set_ui(self.server, cfg, self.holder)
        self.Set_event()

    def _Set_ui(
        self,
        server: viser.ViserServer,
        cfg: Action_Config,
        element_holder: dict[str, Any]
    ):
        if isinstance(cfg.contents, list):
            for _cfg in cfg.contents:
                if _cfg.element_type == "folder":
                    with server.gui.add_folder(_cfg.name):
                        self._Set_ui(server, _cfg, element_holder)
                else:
                    self._Set_ui(server, _cfg, element_holder)
        else:
            _comp_function = getattr(
                server.gui, f"add_{cfg.element_type}")
            if cfg.name == "":
                _component = _comp_function(**cfg.contents)
            else:
                _component = _comp_function(label=cfg.name, **cfg.contents)

            element_holder[f"{cfg.name}_{cfg.element_type}"] = _component

    def Set_event(self):
        raise NotImplementedError

    def Get_http_address(self):
        _server = self.server

        if self.isRunning():
            return (
                True,
                QUrl(f"http://{_server.get_host()}:{_server.get_port()}")
            )
        return False, QUrl()
