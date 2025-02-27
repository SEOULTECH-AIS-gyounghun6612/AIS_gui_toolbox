from __future__ import annotations

from typing import Literal, Any
from dataclasses import dataclass, field, InitVar

from PySide6.QtWidgets import (QWidget, QDialog, QLayout)
from python_ex.project import Config

from .widget import Interface_Config, Get_layout, Get_widget


@dataclass
class Page_Config(Config.Basement):
    interface: InitVar[dict[str, Any]]
    sub_page: InitVar[dict[str, dict[str, Any]]]

    title: str
    window_type: Literal["page", "popup"]
    position: list[int] | None

    interface_cfg: Interface_Config = field(init=False)

    data_cfg: dict[str, Any]

    sub_page_cfg: dict[str, Page_Config] = field(init=False)

    def __post_init__(
        self,
        interface: dict[str, Any],
        sub_page: dict[str, dict[str, Any]]
    ):
        self.interface_cfg = Interface_Config(**interface)
        self.sub_page_cfg = dict((
            _k, Page_Config(**_v)
        ) for _k, _v in sub_page.items())

    def Config_to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "window_type": self.window_type,
            "position": self.position,
            "data_cfg": self.data_cfg,
            "interface": self.interface_cfg.Config_to_dict(),
            "sub_page": dict((
                _k, _sub_page_cfg.Config_to_dict()
            ) for _k, _sub_page_cfg in self.sub_page_cfg.items())
        }


class Page():
    def _Set_interface(self, cfg: Interface_Config):
        raise NotImplementedError

    def _Make_ui(
        self, cfg: Interface_Config
    ) -> tuple[QLayout | QWidget, list[int]]:
        _type = cfg.element_type
        _children = cfg.children_cfg

        if _children:
            # layout
            return (
                Get_layout(
                    _type, [self._Make_ui(_cfg) for _cfg in _children]),
                cfg.size
            )

        # widget
        _widget = Get_widget(cfg)

        # add to class attribute
        if cfg.is_attribute:
            setattr(self, cfg.Make_attribute_name(), _widget)
        return _widget, cfg.size

    def _Set_data(self, **kwarg: Any):
        raise NotImplementedError


class Popup_Page(QDialog, Page):
    def __init__(
        self,
        cfg: Page_Config,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent, modal=cfg.window_type == "popup")

        self.setWindowTitle(cfg.title)
        if cfg.position is not None:
            self.setGeometry(*cfg.position)

        self._Set_interface(cfg.interface_cfg)
        self._Set_data(**cfg.data_cfg)

        self.cfg = cfg

    def _Set_interface(self, cfg: Interface_Config):
        _interface, _ = self._Make_ui(cfg)

        if isinstance(_interface, QWidget):
            _main_layout = QLayout()
            _main_layout.addWidget(_interface)
            self.setLayout(_main_layout)
        else:
            self.setLayout(_interface)
