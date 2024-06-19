import sys
from enum import Enum
from typing import List

from PySide6.QtWidgets import \
    QApplication, \
    QWidget, QDialog, QMessageBox, QFileDialog

from python_ex.system import Path, File


class Param():
    class Interaction_Icon(Enum):
        NO          = QMessageBox.Icon.NoIcon
        QUESTION    = QMessageBox.Icon.Question
        INFO        = QMessageBox.Icon.Information
        WARNING     = QMessageBox.Icon.Warning
        CRITICAL    = QMessageBox.Icon.Critical

    class Interaction_Btn(Enum):
        OK = QMessageBox.StandardButton.Ok
        NO = QMessageBox.StandardButton.No
        RE = QMessageBox.StandardButton.Retry

    class search_filter(Enum):
        ALL     = "All Files(*.*)"
        DATA    = "Data Files (*.csv *.xls *.xlsx, *.json)"
        IMAGE   = "Images (*.png *.xpm *.jpg *.gif)"


class GUI_base():
    class Page(QWidget):
        def __init__(self, title: str):
            super().__init__()
            self.setWindowTitle(title)
            self.draw_layout()

        def get_layout(self):
            GUI_base.Interaction.Pop_up_msg_box(
                title="GUI ERROR",
                message="You don't make {} GUI init. please make the init function".format(self.windowTitle()),
                icon=Param.Interaction_Icon.CRITICAL,
                buttons=[Param.Interaction_Btn.OK, ])
            return None

        def draw_layout(self):
            _layout = self.get_layout()
            self.setLayout(_layout) if _layout is not None else None

    class Interaction():
        @staticmethod
        def Pop_up_msg_box(title: str, message: str, icon: Param.Interaction_Icon, buttons: List[Param.Interaction_Btn]):
            _msg = QMessageBox()
            _msg.setIcon(icon.value)
            _msg.setWindowTitle(title)
            _msg.setText(message)

            bt_flag = buttons[0].value

            if len(buttons) > 1:
                for _button in buttons[1:]:
                    bt_flag = bt_flag | _button.value

            _msg.setStandardButtons(bt_flag)
            _msg.exec_()

        @staticmethod
        def Search(title: str, dir: str, search_filter: List[Param.search_filter] | None = None, parent: QWidget | None = None):
            _dir = Path.Seperater_check(dir)

            if search_filter is None:
                _get_datas = QFileDialog.getExistingDirectory(parent=parent, caption=title, dir=_dir)
            else:
                _filter_str = ""
                for _filter in search_filter:
                    _filter_str += f"{_filter};;"

                _get_datas = QFileDialog.getOpenFileNames(parent=parent, caption=title, dir=_dir, filter=_filter_str[:-2])[0]
                _get_datas = [_base.directory._slash_check(data, is_file=True) for data in _get_datas]

            return _dir, _get_datas

        class subpage(QDialog):
            def __init__(self, title: str):
                super().__init__()
                self.setWindowTitle(title)
                self.draw_layout()

            def draw_layout(self):
                _layout = self.get_layout()
                self.setLayout(_layout) if _layout is not None else None

            def get_layout(self):
                GUI_base.Interaction.Pop_up_msg_box(
                    title="GUI ERROR",
                    message="You don't make {} GUI init. please make the init function".format(self.windowTitle()),
                    icon=Param.Msg_Box.Interaction_Icon.CRITICAL,
                    buttons=[Param.Msg_Box.Btn.OK, ])
                return None

            def onOKButtonClicked(self):
                self.accept()

            def onCancelButtonClicked(self):
                self.reject()

    class event():
        pass


class Application():
    def __init__(self, position: List[int]) -> None:
        self.process = QApplication(sys.argv)
        self.position = position

    def set_root_page(self, root_page: GUI_base.Page):
        self.root_page = root_page

    def _start(self):
        self.root_page.show()
        _position = [self.position[1], self.position[0], self.position[3], self.position[2]]
        self.root_page.setGeometry(*_position)

    def _end(self):
        return self.process.exec()
