from __future__ import annotations

from typing import Literal, Any
from dataclasses import dataclass, field, InitVar

from PySide6.QtWidgets import (QMainWindow, QWidget, QDialog, QLayout)
from python_ex.project import Config


@dataclass
class Page_Config(Config.Basement):
    interface: InitVar[dict[str, dict[str, Any]]] = field(
        default_factory=lambda: Page_Config().Config_to_dict())

    title: str = "page"
    window_type: Literal["page", "popup"] = "page"
    position: tuple[int, int, int, int] | None = None

    data_cfg: dict[str, Any] = field(default_factory=dict)
    interface_cfg: dict[str, Page_Config] = field(default_factory=dict)

    def __post_init__(self, **meta: dict[str, Any]):
        self.interface_cfg = dict((
            _k, Page_Config(**_kwarg)
        ) for _k, _kwarg in meta["interface"].items())

    def Config_to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "window_type": self.window_type,
            "position": self.position,
            "data_cfg": self.data_cfg,
            "interface": dict((
                _k, _act_cfg.Config_to_dict()
            ) for _k, _act_cfg in self.interface_cfg.items())
        }


class Page(QWidget):
    def __init__(
        self,
        cfg: Page_Config,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(cfg.title)

        if cfg.position is not None:
            self.setGeometry(*cfg.position)

        _layout = self.Get_interface(**cfg.interface_cfg)

        if hasattr(self, "setCentralWidget"):
            _main_widget = QWidget()
            _main_widget.setLayout(_layout)
            getattr(self, "setCentralWidget")(_main_widget)
        else:
            self.setLayout(_layout)

        self._Set_data(**cfg.data_cfg)
        self._Set_event()

        self.cfg = cfg

    def Get_interface(self, **cfgs: Page_Config) -> QLayout:
        raise NotImplementedError

    def _Set_event(self):
        raise NotImplementedError

    def _Set_data(self, **kwarg: Any):
        raise NotImplementedError


class Popup_Page(QDialog, Page):
    def __init__(
        self,
        cfg: Page_Config,
        parent: QWidget | None = None
    ) -> None:
        QDialog.__init__(self, parent, modal=cfg.window_type == "popup")
        Page.__init__(self, cfg, self)
