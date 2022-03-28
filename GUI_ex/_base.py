import sys
from enum import Enum
from typing import List

from PySide2.QtWidgets import \
    QApplication,\
    QWidget, QDialog, QMessageBox, QFileDialog

from python_ex import _base


class Param():
    class msg_box():
        class icon(Enum):
            NO          = QMessageBox.NoIcon
            QUESTION    = QMessageBox.Question
            INFO        = QMessageBox.Information
            WARNING     = QMessageBox.Warning
            CRITICAL    = QMessageBox.Critical

        class btn(Enum):
            OK = QMessageBox.Ok
            NO = QMessageBox.No
            RE = QMessageBox.Retry

    class search_filter(Enum):
        ALL     = "All Files(*.*)"
        DATA    = "Data Files (*.csv *.xls *.xlsx, *.json)"
        IMAGE   = "Images (*.png *.xpm *.jpg *.gif)"


class GUI_base():
    class page(QWidget):
        def __init__(self, title: str):
            super().__init__()
            self.setWindowTitle(title)
            self.draw_layout()

        def get_layout(self):
            GUI_base.interaction.msg_box(
                title="GUI ERROR",
                message="You don't make {} GUI init. please make the init function".format(self.windowTitle()),
                icon=Param.msg_box.icon.CRITICAL,
                buttons=[Param.msg_box.btn.OK, ])
            return None

        def draw_layout(self):
            _layout = self.get_layout()
            self.setLayout(_layout) if _layout is not None else None

    class interaction():
        @staticmethod
        def msg_box(title: str, message: str, icon: Param.msg_box.icon, buttons: List[Param.msg_box.btn]):
            _msg = QMessageBox()
            _msg.setIcon(icon.value)
            _msg.setWindowTitle(title)
            _msg.setText(message)

            bt_flag = 0
            for _button in buttons:
                bt_flag = bt_flag | _button.value

            _msg.setStandardButtons(bt_flag)
            _msg.exec_()

        @staticmethod
        def search(title: str, directory: str, search_filter: List[Param.search_filter] = None, parent: QWidget = None):
            _dir = _base.directory._slash_check(directory)

            if search_filter is None:
                _get_datas = QFileDialog.getExistingDirectory(parent=parent, caption=title, directory=_dir)
                _get_datas = [_base.directory._slash_check(data) for data in _get_datas]
            else:
                _filter_str = ""
                for _filter in search_filter:
                    _filter_str += f"{_filter};;"

                _get_datas = QFileDialog.getOpenFileNames(parent=parent, caption=title, directory=_dir, filter=_filter_str[:-2])[0]
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
                GUI_base.interaction.msg_box(
                    title="GUI ERROR",
                    message="You don't make {} GUI init. please make the init function".format(self.windowTitle()),
                    icon=Param.msg_box.icon.CRITICAL,
                    buttons=[Param.msg_box.btn.OK, ])
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

    def set_root_page(self, root_page: GUI_base.page):
        self.root_page = root_page

    def _start(self):
        self.root_page.show()
        _position = [self.position[1], self.position[0], self.position[3], self.position[2]]
        self.root_page.setGeometry(*_position)

    def _end(self):
        return self.process.exec_()
