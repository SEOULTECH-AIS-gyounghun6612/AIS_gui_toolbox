from __future__ import annotations
from typing import Any, Literal
from dataclasses import dataclass

import numpy as np

from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QObject, Signal, QThread, QUrl

from PySide6.QtWidgets import (QFrame, QLabel, QWidget)
from PySide6.QtWebEngineWidgets import QWebEngineView

from python_ex.project import Config
import viser


class Line(QFrame):
    def __init__(
        self,
        is_horizontal: bool,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setFrameShape(
            QFrame.Shape.HLine if is_horizontal else QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class Image_Display_Widget(QLabel):
    """
    이미지 데이터를 Pixmap으로 변환하여 표시하는 위젯.

    ### Attributes:
        is_init_fail (Signal): 이미지 변환 실패 시 신호를 발생시키는 시그널.
    """
    # signal
    is_init_fail: Signal = Signal(int)

    def Update_pixmap(self, img: np.ndarray):
        """
        NumPy 배열 이미지를 QPixmap으로 변환하여 QLabel에 표시.

        ### Args:
        img (np.ndarray): 변환할 이미지 배열 (Grayscale, RGB, RGBA 사용).

        ### Returns:
            bool: 변환 및 적용 성공 여부. 실패 시 False 반환.
        """
        if img.ndim > 3:
            self.is_init_fail.emit(1)  # input data is not image
            return False

        if img.ndim == 2:  # Grayscale
            _format = QImage.Format.Format_Grayscale8 if (
                img.dtype == np.uint8) else QImage.Format.Format_Grayscale16
        elif img.shape[2] == 3:  # RGB
            _format = QImage.Format.Format_RGB888
        elif img.shape[2] == 4:  # RGBA
            _format = QImage.Format.Format_RGBA8888
        else:
            self.is_init_fail.emit(1)  # input data is not image
            return False

        _h, _w = img.shape[:2]
        self.setPixmap(QPixmap.fromImage(QImage(img.data, _w, _h, _format)))
        return True


class Viser():
    @dataclass
    class User_Interface_Config(Config.Basement):
        name: str
        element_type: Literal[
            "folder",
            "number", "text", "vector2", "vector3", "rgb",
            "slider", "multi_slider", "progress_bar",
            "upload_button", "button", "checkbox",
        ] | None
        contents: dict[str, Any] | list[Viser.User_Interface_Config]

        def Config_to_dict(self) -> dict[str, Any]:
            _con = self.contents

            return {
                "name": self.name,
                "element_type": self.element_type,
                "contents": [
                    _i.Config_to_dict() for _i in _con
                ] if isinstance(_con, list) else _con
            }

    @staticmethod
    def Make_cfg_from_dict(
        structure: dict[str, Any]
    ) -> Viser.User_Interface_Config:
        def l2t(data: list):
            return tuple(
                l2t(_d) if isinstance(_d, list) else _d for _d in data)

        _con: list[dict[str, Any]] | dict[str, Any] = structure["contents"]

        if isinstance(_con, list):
            structure["contents"] = [
                Viser.Make_cfg_from_dict(_data) for _data in _con]
        else:
            structure["contents"] = dict(
                (
                    _k, l2t(_v) if isinstance(_v, list) else _v
                ) for _k, _v in _con.items()
            )

        return Viser.User_Interface_Config(**structure)

    class Server(QThread):
        def __init__(
            self,
            cfg: Viser.User_Interface_Config,
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
            cfg: Viser.User_Interface_Config,
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

    class Viewer(QWebEngineView):
        def __init__(
            self,
            viser_server: Viser.Server
        ):
            super().__init__()
            _host = viser_server.server.get_host()
            _port = viser_server.server.get_port()

            if not viser_server.isRunning():
                viser_server.start()
            self.load(QUrl(f"http://{_host}:{_port}"))
            self.viser_server = viser_server
