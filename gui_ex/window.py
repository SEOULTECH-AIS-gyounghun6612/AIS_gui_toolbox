import sys
from enum import Enum
from typing import List

from PySide6.QtWidgets import (
    QWidget, QDialog, QMessageBox, QFileDialog, QMainWindow
)

# from python_ex.system import Path


class Message_Box_Flag():
    class Icon(Enum):
        NO          = QMessageBox.Icon.NoIcon
        QUESTION    = QMessageBox.Icon.Question
        INFO        = QMessageBox.Icon.Information
        WARNING     = QMessageBox.Icon.Warning
        CRITICAL    = QMessageBox.Icon.Critical

    class Btn(Enum):
        OK = QMessageBox.StandardButton.Ok
        NO = QMessageBox.StandardButton.No
        RE = QMessageBox.StandardButton.Retry


class Interaction_Dialog():
    @staticmethod
    def Message_box_pop_up(
        title: str,
        message: str,
        icon: Message_Box_Flag.Icon,
        buttons: List[Message_Box_Flag.Btn]
    ):
        _msg = QMessageBox()
        _msg.setIcon(icon.value)
        _msg.setWindowTitle(title)
        _msg.setText(message)

        bt_flag = buttons[0].value

        if len(buttons) > 1:
            for _button in buttons[1:]:
                bt_flag = bt_flag | _button.value

        _msg.setStandardButtons(bt_flag)

        return _msg.exec_()

    @staticmethod
    def Get_directory():
        ...

    @staticmethod
    def Get_file_from_directory():
        ...


class Default_Window():
    class Main(QMainWindow):
        ...

    class Sub():
        ...
