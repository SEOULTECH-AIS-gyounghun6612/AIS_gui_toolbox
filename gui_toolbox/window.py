from __future__ import annotations

from typing import Literal, Any
from dataclasses import dataclass, field, InitVar

from PySide6.QtWidgets import (QWidget, QDialog, QLayout)
from python_ex.project import Config


@dataclass
class Page_Config(Config.Basement):
    sub_page_meta: InitVar[dict[str, dict[str, Any]]]

    title: str = "page"
    window_type: Literal["page", "popup"] = "page"
    position: tuple[int, int, int, int] | None = None

    data_cfg: dict[str, Any] = field(default_factory=dict)
    sub_page: dict[str, Page_Config] = field(default_factory=dict)

    def __post_init__(
        self,
        sub_page_meta: dict[str, dict[str, Any]]
    ):
        self.sub_page = dict((
            _k, Page_Config(**_kwarg)
        ) for _k, _kwarg in sub_page_meta.items())

    def Config_to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "window_type": self.window_type,
            "position": self.position,
            "data_cfg": self.data_cfg,
            "sub_page_meta": dict((
                _k, _act_cfg.Config_to_dict()
            ) for _k, _act_cfg in self.sub_page.items())
        }


class Popup_Page(QDialog):
    def __init__(
        self,
        cfg: Page_Config,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent, modal=cfg.window_type == "popup")
        self.setWindowTitle(cfg.title)

        if cfg.position is not None:
            self.setGeometry(*cfg.position)

        self.setLayout(self.Get_interface())
        self._Set_data(**cfg.data_cfg)
        self._Set_event()

        self.cfg = cfg

    def Get_interface(self) -> QLayout:
        raise NotImplementedError

    def _Set_event(self):
        raise NotImplementedError

    def _Set_data(self, **kwarg: Any):
        raise NotImplementedError
