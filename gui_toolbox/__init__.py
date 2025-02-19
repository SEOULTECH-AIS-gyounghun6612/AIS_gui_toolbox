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


@dataclass
class App_Config(Config.Basement):
    # interface
    bar_structures: InitVar[dict[str, list[dict]]]

    title: str = "application"
    position: tuple[int, int, int, int] = field(
        default_factory=lambda: (200, 100, 300, 200))

    bar_configs: dict[str, list[Bar_Config]] = field(
        default_factory=dict)

    main_layout: dict[str, Any] = field(default_factory=dict)

    # for sub-window
    sub_widget_cfg_file: dict[str, str] = field(default_factory=dict)
    sub_widget_data: dict[str, str] = field(default_factory=dict)

    def __post_init__(
        self,
        action_structure: dict[str, list[dict]]
    ):
        self.bar_configs = dict((
            _bar_type, [self.Make_bar_config(**_arg) for _arg in _args]
        ) for _bar_type, _args in action_structure.items())

    @dataclass
    class Bar_Config():
        name: str
        info: str | list[App_Config.Bar_Config] | None

        shortcut: str | None
        with_shift: bool = False
        icon: str | None = None

        def Config_to_dict(self):
            _info = self.info
            return {
                "name": self.name,
                "info": [
                    _i.Config_to_dict() for _i in _info
                ] if isinstance(_info, list) else _info,
                "shortcut": self.shortcut,
                "with_shift": self.with_shift,
                "icon": self.icon,
            }

    def Make_bar_config(
        self,
        name: str,
        info: list[dict] | str,
        shortcut: str | None,
        with_shift: bool,
        icon: str | None
    ) -> Bar_Config:
        if isinstance(info, list):
            # make node for add to action in under
            _info = [self.Make_bar_config(**_arg) for _arg in info]
            return self.Bar_Config(name, _info, shortcut, with_shift, icon)

        # make action node
        return self.Bar_Config(name, info, shortcut, with_shift, icon)

    def Config_to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "position": self.position,
            "bar_structures": dict((
                _k, [_bar_config.Config_to_dict() for _bar_config in _list]
            ) for _k, _list in self.bar_configs.items()),
            "main_layout": dict((
                _k,
                _v.Config_to_dict() if isinstance(_v, Config.Basement) else _v
            ) for _k, _v in self.main_layout.items()),
            "sub_widget_cfg_file": self.sub_widget_cfg_file,
            "sub_widget_data": self.sub_widget_data
        }


class App(QMainWindow):
    def __init__(
        self,
        config_format: type[App_Config],
        config_path: Path
    ) -> None:
        self.app = QApplication(sys.argv)
        super().__init__()

        self.config_path = config_path
        if config_path.exists():
            _cfg = Config.Read_from_file(config_format, config_path)
        else:
            _cfg = config_format({})

        self.setWindowTitle(_cfg.title)

        if _cfg.bar_configs:
            if "menubar" in _cfg.bar_configs:
                _menu = self.menuBar()
                _menu_action_cfg = _cfg.bar_configs["menubar"]
                self._Set_menu_bar(_menu, _menu_action_cfg)

        # if _cfg.menubar_structure:
        #     self.addToolBar(self._Set_menu_bar(**_cfg.menubar_structure))

        _main_widget = QWidget()
        _main_widget.setLayout(
            self._Set_main_layout(_cfg.main_layout))
        self.setCentralWidget(_main_widget)
        self.setGeometry(*_cfg.position)

        self.cfg = _cfg

    def _Set_menu_bar(
        self,
        menu_node: QMenuBar | QMenu,
        action_cfgs: list[App_Config.Bar_Config]
    ):
        for _cfg in action_cfgs:
            if isinstance(_cfg.info, str):
                _action = QAction(_cfg.name, self)
                _action.triggered.connect(
                    self.__class__.__dict__[_cfg.info])
                if _cfg.icon is not None and Path(_cfg.icon).exists():
                    _action.setIcon(QIcon(_cfg.icon))

                if _cfg.shortcut is not None:
                    _c = _cfg.shortcut[0]
                    _action.setShortcut(
                        QKeySequence(
                            f"Ctrl+{f'Shift+{_c}' if _cfg.with_shift else _c}")
                    )
                menu_node.addAction(_action)
            elif isinstance(_cfg.info, list):
                # add sub menu
                self._Set_menu_bar(menu_node.addMenu(_cfg.name), _cfg.info)
            else:
                menu_node.addSeparator()

    def _Set_main_layout(self, main_layout_cfg: dict[str, str]) -> QLayout:
        raise NotImplementedError

    def Run(self):
        self.show()
        _status = self.app.exec_()

        _config_path = self.config_path.parent
        _config_path.mkdir(parents=True, exist_ok=True)

        Write_to(self.config_path, self.cfg.Config_to_dict())

        return sys.exit(_status)
