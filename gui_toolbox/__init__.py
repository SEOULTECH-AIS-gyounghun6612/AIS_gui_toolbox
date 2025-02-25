from __future__ import annotations

from typing import Any
import sys
from dataclasses import dataclass, field, InitVar
from pathlib import Path

from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QWidget, QMenu, QMenuBar, QLayout, QMainWindow  # QDialog
)

from python_ex.file import Write_to
from python_ex.project import Config

from .window import Page_Config


@dataclass
class Action_Config(Config.Basement):
    name: str
    info: str | list[Action_Config] | None

    hotkey: str | None
    with_shift: bool = False
    icon: str | None = None

    def Config_to_dict(self):
        _info = self.info
        return {
            "name": self.name,
            "info": [
                _i.Config_to_dict() for _i in _info
            ] if isinstance(_info, list) else _info,
            "hotkey": self.hotkey,
            "with_shift": self.with_shift,
            "icon": self.icon,
        }


@dataclass
class App_Config(Config.Basement):
    action: InitVar[dict[str, dict[str, Any]]]
    sub_page: InitVar[dict[str, dict[str, Any]]]

    title: str = "application"
    position: tuple[int, int, int, int] = (100, 100, 100, 100)
    action_cfg: dict[str, Action_Config] = field(default_factory=dict)

    data_cfg: dict[str, Any] = field(default_factory=dict)
    sub_page_cfg: dict[str, Page_Config] = field(default_factory=dict)

    def __post_init__(
        self,
        action: dict[str, dict[str, Any]],
        sub_page: dict[str, dict[str, Any]]
    ):
        self.sub_page_cfg = dict((
            _k, Page_Config(**_v)
        ) for _k, _v in sub_page.items())
        self.action_cfg = dict((
            _k, Action_Config(**_v)
        ) for _k, _v in action.items())

    def Config_to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "position": self.position,
            "action": dict((
                _k, _act_cfg.Config_to_dict()
            ) for _k, _act_cfg in self.action_cfg.items()),
            "data_cfg": self.data_cfg,
            "sub_page": dict((
                _k, _sub_page_cfg.Config_to_dict()
            ) for _k, _sub_page_cfg in self.sub_page_cfg.items())
        }


class Application(QMainWindow):
    def __init__(self, cfg_format: type[App_Config], cfg_path: Path):
        self.app = QApplication(sys.argv)
        super().__init__()

        self.config_path = cfg_path
        if cfg_path.exists():
            _cfg = Config.Read_from_file(cfg_format, cfg_path)
        else:
            _cfg = cfg_format(
                {},
                Page_Config({}).Config_to_dict()
            )

        self.setWindowTitle(_cfg.title)

        if "menubar" in _cfg.action_cfg:
            _menu = self.menuBar()
            self._Set_menubar(_menu, _cfg.action_cfg["menubar"])

        _main_widget = QWidget()
        _main_widget.setLayout(self.Get_interface())
        self.setCentralWidget(_main_widget)
        if _cfg.position is not None:
            self.setGeometry(*_cfg.position)

        self._Set_data(**_cfg.data_cfg)
        self._Set_event()

        self.cfg = _cfg

    def _Set_menubar(self, menu_node: QMenuBar | QMenu, cfg: Action_Config):
        _name = cfg.name
        _info = cfg.info

        if _info is None:
            menu_node.addSeparator()
        elif isinstance(_info, str):
            # make action and set in this level
            _action = QAction(_name, self)

            _icon = cfg.icon
            _action.triggered.connect(getattr(self, _info))
            if _icon is not None and Path(_icon).exists():
                _action.setIcon(QIcon(_icon))

            _hotkey = cfg.hotkey
            _with_sft = cfg.with_shift
            if _hotkey is not None:
                _c = _hotkey[0]
                _action.setShortcut(
                    QKeySequence(f"Ctrl+{f'Shift+{_c}' if _with_sft else _c}")
                )
            menu_node.addAction(_action)
        else:
            # in to the next level
            _next_lvl = menu_node.addMenu(_name)
            for _cfg in _info:
                self._Set_menubar(_next_lvl, _cfg)

    def Get_interface(self) -> QLayout:
        raise NotImplementedError

    def _Set_event(self):
        raise NotImplementedError

    def _Set_data(self, **kwarg: Any):
        raise NotImplementedError

    def Run(self):
        self.show()
        _status = self.app.exec_()

        _config_path = self.config_path.parent
        _config_path.mkdir(parents=True, exist_ok=True)

        Write_to(self.config_path, self.cfg.Config_to_dict())

        return sys.exit(_status)
