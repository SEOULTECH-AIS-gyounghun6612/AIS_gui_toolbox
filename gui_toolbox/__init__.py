from __future__ import annotations
# from typing import Literal

import sys
# from pathlib import Path

from PySide6.QtWidgets import QApplication
from .core import Main_Window


class Application_Template():
    def __init__(self, main_window: Main_Window):
        self.app = QApplication(sys.argv)
        self.main_window = main_window

    def Watcher(self):
        self.main_window.show()  # display UI
        self.main_window.Run()
        _status = self.app.exec_()
        self.main_window.Stop()

        return sys.exit(_status)
