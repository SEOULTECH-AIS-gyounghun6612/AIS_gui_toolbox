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
    child: InitVar[list[dict[str, Any]] | str | None] = "function_name"

    hotkey: str | None = "e"
    with_shift: bool = False
    icon: str | None = None

    child_cfg: list[Action_Config] | str | None = field(init=False)

    def __post_init__(self, child: str | list[dict[str, Any]] | None):
        if isinstance(child, list):
            self.child_cfg = [Action_Config(**_cfg) for _cfg in child]
        else:
            self.child_cfg = child

    def Config_to_dict(self):
        _child = self.child_cfg
        return {
            "name": self.name,
            "child": [
                _i.Config_to_dict() for _i in _child
            ] if isinstance(_child, list) else _child,
            "hotkey": self.hotkey,
            "with_shift": self.with_shift,
            "icon": self.icon,
        }


@dataclass
class App_Config(Page_Config):
    action: InitVar[list[dict[str, Any]]]
    action_cfg: list[Action_Config] = field(init=False)

    def __post_init__(
        self,
        interface: dict[str, Any],
        sub_page: dict[str, str | None],
        action: list[dict[str, Any]]
    ):
        super().__post_init__(interface, sub_page)

        self.action_cfg = [
            Action_Config(**_v) for _v in action
        ] if action else [Action_Config("menu_01", [], None)]

    def Config_to_dict(self) -> dict[str, Any]:
        return {
            **super().Config_to_dict(),
            "action": [
                _cfg.Config_to_dict() for _cfg in self.action_cfg
            ]
        }


class App(QMainWindow, Page):
    def __init__(self, cfg_format: type[App_Config], cfg_path: Path):
        self.app = QApplication(sys.argv)
        self.config_path = cfg_path
        if cfg_path.exists():
            _cfg = Config.Read_from_file(cfg_format, cfg_path)
        else:
            _cfg = cfg_format(
                **App_Config(
                    interface=Interface_Config([]).Config_to_dict(),
                    sub_page={},
                    action=[],
                    title="application",
                    window_type="page",
                    position=[100, 100, 300, 500],
                    data_cfg={},
                ).Config_to_dict())

        super().__init__(None)

        self.setWindowTitle(_cfg.title)
        if _cfg.position is not None:
            self.setGeometry(*_cfg.position)

        self._Set_interface(_cfg.interface_cfg)
        self._Set_data(**_cfg.data_cfg)

        if _cfg.action_cfg:
            _menu = self.menuBar()
            for _action_cfg in _cfg.action_cfg:
                self._Set_menubar(_menu, _action_cfg)

        self.cfg = _cfg

        self._Run()

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
        _info = cfg.child_cfg

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

    def _Run(self):
        raise NotImplementedError

    def _Stop(self):
        raise NotImplementedError

    def Watcher(self):
        _status = self.app.exec_()

        self._Stop()

        _config_path = self.config_path.parent
        _config_path.mkdir(parents=True, exist_ok=True)

        Write_to(self.config_path, self.cfg.Config_to_dict())

        return sys.exit(_status)
