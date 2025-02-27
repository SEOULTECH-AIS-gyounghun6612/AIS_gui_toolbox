from __future__ import annotations

from typing import Any
import sys
from dataclasses import dataclass, field, InitVar
from pathlib import Path

from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMenu, QMenuBar, QMainWindow, QWidget
)

from python_ex.file import Write_to
from python_ex.project import Config

from .window import Page_Config, Page
from .widget import Interface_Config


@dataclass
class Action_Config(Config.Basement):
    name: str = "action_name"
    info: str | list[Action_Config] | None = "function_name"

    hotkey: str | None = None
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
class App_Config(Page_Config):
    action: InitVar[dict[str, dict[str, Any]]] = field(
        default_factory=lambda: Action_Config().Config_to_dict())
    action_cfg: dict[str, Action_Config] = field(default_factory=dict)

    def __post_init__(self, **meta: dict[str, Any]):
        super().__post_init__(**meta)
        self.action_cfg = dict((
            _k, Action_Config(**_v)
        ) for _k, _v in meta["action"].items())

    def Config_to_dict(self) -> dict[str, Any]:
        return {
            **super().Config_to_dict(),
            "action": dict((
                _k, _action_cfg.Config_to_dict()
            ) for _k, _action_cfg in self.action_cfg.items())
        }


class App(QMainWindow, Page):
    def __init__(self, cfg_format: type[App_Config], cfg_path: Path):
        self.app = QApplication(sys.argv)
        super().__init__()

        self.config_path = cfg_path
        if cfg_path.exists():
            _cfg = Config.Read_from_file(cfg_format, cfg_path)
        else:
            _cfg = cfg_format(**Page_Config().Config_to_dict())

        QMainWindow.__init__(self)
        Page.__init__(self, _cfg, self)

        if "menubar" in _cfg.action_cfg:
            _menu = self.menuBar()
            self._Set_menubar(_menu, _cfg.action_cfg["menubar"])

    def _Set_interface(self, cfg: Interface_Config):
        _interface, _ = self._Make_ui(cfg)

        if isinstance(_interface, QWidget):
            self.setCentralWidget(_interface)
        else:
            _main_widget = QWidget()
            _main_widget.setLayout(_interface)
            self.setCentralWidget(_main_widget)

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

    def Run(self):
        self.show()
        _status = self.app.exec_()

        _config_path = self.config_path.parent
        _config_path.mkdir(parents=True, exist_ok=True)

        Write_to(self.config_path, self.cfg.Config_to_dict())

        return sys.exit(_status)
