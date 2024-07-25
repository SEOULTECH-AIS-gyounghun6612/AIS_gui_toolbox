from enum import Enum
from typing import Any
import sys

from PySide6.QtWidgets import (
    QApplication, QWidget, QToolBar,
    QMessageBox, QMainWindow,
    QFileDialog,  # QDialog
)


# from python_ex.system import Path
class Message_Box_Flag():
    class Icon(Enum):
        NO =        QMessageBox.Icon.NoIcon
        QUESTION =  QMessageBox.Icon.Question
        INFO =      QMessageBox.Icon.Information
        WARNING =   QMessageBox.Icon.Warning
        CRITICAL =  QMessageBox.Icon.Critical

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
        buttons: list[Message_Box_Flag.Btn]
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
    def Get_file_from_directory(caption: str, obj_dir: str):
        return QFileDialog.getExistingDirectory(
            None,
            caption,
            obj_dir,
            QFileDialog.Option.ShowDirsOnly
        )


class Default_Window():
    class Main(QMainWindow):
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

    # class Sub():
    #     ...

    class Page(QWidget):
        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)
            self._User_interface_init()

        def _User_interface_init(self):
            raise NotImplementedError
