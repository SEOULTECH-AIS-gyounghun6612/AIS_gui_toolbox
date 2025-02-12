from typing import Any
import sys

from PySide6.QtWidgets import (
    QApplication, QWidget, QToolBar, QLayout,
    QMessageBox, QMainWindow,
    QFileDialog,  # QDialog
)

from python_ex.project import Config


class App_Config(Config):
    ...


class App(QMainWindow):
    def __init__(
        self,
        title,
        position: list[int],
        default_opt: dict[str, dict[str, Any]] | None = None
    ) -> None:
        self.app = QApplication(sys.argv)
        super().__init__()

        self.setWindowTitle(title)
        _main_widget = self._Set_main_widget()
        self.setCentralWidget(_main_widget)

        _toolbar = self._Set_tool_bar(default_opt)
        if _toolbar is not None:
            self.addToolBar(_toolbar)
        self.setGeometry(*position)

    def _Set_tool_bar(
        self, default_opt: dict[str, dict[str, Any]] | None
    ) -> QToolBar | None:
        raise NotImplementedError

    def _Set_main_widget(self) -> QWidget:
        raise NotImplementedError

    def Run(self):
        self.show()

        return self.app.exec_()
