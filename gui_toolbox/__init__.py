import sys
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QToolBar, QLayout, QMainWindow  # QDialog
)

# from python_ex.system import Path_utils
from python_ex.project import Config


@dataclass
class App_Config(Config.Basement):
    # interface
    title: str = "application"
    position: tuple[int, int, int, int] = field(
        default_factory=lambda: (200, 100, 300, 200))
    toolbar_structure: dict[str, str] = field(default_factory=dict)

    main_layout: dict[str, str] = field(default_factory=dict)

    # for sub-window
    sub_widget_cfg_file: dict[str, str] = field(default_factory=dict)
    sub_widget_data: dict[str, str] = field(default_factory=dict)


class App(QMainWindow):
    def __init__(
        self,
        config_format: type[App_Config],
        config_path: Path
    ) -> None:
        self.app = QApplication(sys.argv)
        super().__init__()

        if config_path.exists():
            _cfg = Config.Read_from_file(config_format, config_path)
        else:
            _cfg = config_format()

        self.setWindowTitle(_cfg.title)

        if _cfg.toolbar_structure:
            self.addToolBar(self._Set_tool_bar(**_cfg.toolbar_structure))

        _main_widget = QWidget()
        _main_widget.setLayout(
            self._Set_main_layout(_cfg.main_layout))
        self.setCentralWidget(_main_widget)
        self.setGeometry(*_cfg.position)

        self.cfg = _cfg

    def _Set_tool_bar(self, **cfg) -> QToolBar:
        raise NotImplementedError

    def _Set_main_layout(self, main_layout_cfg: dict[str, str]) -> QLayout:
        raise NotImplementedError

    def Run(self):
        self.show()

        return sys.exit(self.app.exec_())
