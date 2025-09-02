from __future__ import annotations
# from typing import Literal

import sys
# from pathlib import Path

from PySide6.QtWidgets import QApplication
from .core import Main_Window


class Application_Starter():
    def __init__(self):
        self.app = QApplication(sys.argv)

    def Start(self, main_window: Main_Window):
        main_window.show()  # display UI
        main_window.Run()
        _status = self.app.exec_()
        main_window.Stop()

        return sys.exit(_status)