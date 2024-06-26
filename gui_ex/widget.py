from typing import Tuple, Dict, List
from enum import Enum

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QLayout, QGridLayout, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QListWidget,
    QListWidgetItem, QAbstractItemView,
)

from PySide6.QtGui import QPixmap, QImage
import numpy as np

from python_ex.vision import File_IO, Vision_Toolbox, Convert_Flag

from .window import Interaction_Dialog, Message_Box_Flag


class Align(Enum):
    CENTER = Qt.AlignmentFlag.AlignCenter
    RIGHT = Qt.AlignmentFlag.AlignRight
    LEFT = Qt.AlignmentFlag.AlignLeft


def Widget_grouping(
    widgets: List[QWidget],
    is_horizental: bool,
    align: Align | List[Align] | None = None
) -> QLayout:
    _is_list = isinstance(align, list)

    if _is_list and len(align) != len(widgets):
        raise ValueError(
            "!!! Widgets and ailgn count is mismatch. check it !!!")

    _layout = QHBoxLayout() if is_horizental else QVBoxLayout()
    for _ct, _widget in enumerate(widgets):
        if align is None:
            _layout.addWidget(_widget)
        else:
            _ali = align[_ct].value if _is_list else align.value
            _layout.addWidget(_widget, alignment=_ali)
    return _layout


def Widget_grouping_with_rate(
    widgets: List[QWidget],
    is_horizental: bool,
    rate: List[int],
    align: Align | List[Align] | None = None
) -> QLayout:
    _is_list = isinstance(align, list)

    if _is_list and len(align) != len(widgets):
        raise ValueError(
            "!!! Widgets and ailgn count is mismatch. check it !!!")

    if len(rate) != len(widgets):
        raise ValueError(
            "!!! Widgets and rate count is mismatch. check it !!!")

    _layout = QGridLayout()
    _st = 0

    for _ct, (_widget, _rate) in enumerate(zip(widgets, rate)):
        _pos = [_st, 0, _rate, 1] if is_horizental else [0, _st, 1, _rate]
        if align is None:
            _layout.addWidget(_widget, *_pos)
        else:
            _ali = align[_ct].value if _is_list else align.value
            _layout.addWidget(_widget, *_pos, alignment=_ali)
        _st += _rate
    return _layout


def Attach_label(
    obj: QWidget | QLayout,
    label_text: str,
    rate: int = -1
) -> QLayout:
    _is_widget = isinstance(obj, QWidget)
    _is_grid = rate != -1

    if _is_grid:
        _layout = QHBoxLayout()
        _layout.addWidget(QLabel(label_text))
        _layout.addWidget(obj) if _is_widget else _layout.addLayout(obj)

    else:
        _layout = QGridLayout()
        _layout.addWidget(QLabel(label_text), 0, 0)

        if _is_widget:
            _layout.addWidget(obj, 0, 1, 1, rate)
        else:
            _layout.addLayout(obj, 0, 1, 1, rate)

    return _layout


class Img_Dispaly_Widget(QLabel):
    def __init__(
        self,
        parent: QWidget | None = None,
        img: np.ndarray | str | None = None
    ):
        super().__init__(parent)
        self.img, is_img_load = self._Set_img(img, True)
        self.is_img_load = is_img_load

        if is_img_load:
            self.Display()

    def _Set_img(
        self,
        img: np.ndarray | str | None = None,
        is_init: bool = False
    ) -> Tuple[np.ndarray, bool]:
        if img is None:
            # Set empty img, when init module. Else, it is error.
            if not is_init:
                Interaction_Dialog.Message_box_pop_up(
                    "!!! File Load Error !!!",
                    "이미지 데이터 또는 파일이 전달되지 않음",
                    Message_Box_Flag.Icon.WARNING,
                    [Message_Box_Flag.Btn.OK]
                )

            return np.empty(0), False

        _img = File_IO.File_to_img(img) if isinstance(img, str) else img
        if not len(_img.shape):
            Interaction_Dialog.Message_box_pop_up(
                "!!! File Load Error !!!",
                "이미지 파일을 읽는 과정에서 문제 발생",
                Message_Box_Flag.Icon.WARNING,
                [Message_Box_Flag.Btn.OK]
            )
            return _img, False
        else:
            return _img, True

    def _Img_to_pixmap(self):
        _img = self.img
        if len(_img.shape) == 2:  # gray
            if _img.dtype == np.uint8:
                _format = QImage.Format.Format_Grayscale8
            else:
                _format = QImage.Format.Format_Grayscale16
            _bytes_per_line = _img.shape[0]
        elif len(_img.shape) == 3:  # color
            _img = Vision_Toolbox.Format_converter(_img)
            _format = QImage.Format.Format_RGB888
            _bytes_per_line = _img.shape[0] * _img.shape[2]
        else:  # color with a channel
            _img = Vision_Toolbox.Format_converter(
                _img,
                Convert_Flag.BGRA2RGBA
            )
            _format = QImage.Format.Format_RGBA8888
            _bytes_per_line = _img.shape[0] * _img.shape[2]

        _h, _w = _img.shape[:2]
        return QPixmap.fromImage(
            QImage(_img.tobytes(), _w, _h, _bytes_per_line, _format)
        )

    def Display(self, img: np.ndarray | str | None = None):
        _img, _is_img_load = self._Set_img(img, True)

        if not self.is_img_load and _is_img_load:
            return False

        if _is_img_load:
            self.img = _img

        self.setPixmap(self._Img_to_pixmap())
        return True


class Multi_Head_Widget(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.depth: int = -1
        self.header: Dict[Tuple[int, int], Tuple[str, int]] = {}

    def _Get_structure_size(
        self,
        header_structure: Dict[str, int | Dict[str, int | Dict]],
        depth: int = 0,
        order: int = 0
    ):
        self.depth = depth if depth > self.depth else self.depth

        _this_order = order

        for _name, _info in header_structure.items():
            # if this item is leaf header -> _info is row span size
            if isinstance(_info, int):
                self.header[(depth, _this_order)] = (
                    _name, _info
                )
                _this_order = _this_order + _info

            # if this item is not leaf
            else:
                _sub_order = self._Get_structure_size(
                    _info, depth=(depth + 1), order=_this_order
                )
                _span_size = _sub_order - _this_order
                self.header[(depth, _this_order)] = (_name, _span_size)
                _this_order = _sub_order

        return _this_order  # in laset order is header row size

    def User_interface_init(self, header_structure: Dict[str, int | Dict]):
        self._Get_structure_size(header_structure)

        _this_layout = QGridLayout(self)
        _this_layout.setSpacing(0)
        _this_layout.setContentsMargins(0, 0, 0, 0)
        for (_col, _row), (_name, row_span) in self.header.items():
            _col_span = self.depth - _col + 1
            _this_layout.addWidget(
                QLabel(_name), _row, _col, row_span, _col_span)

        self.setLayout(_this_layout)


class Mulit_Head_List_Widget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.header_widget = Multi_Head_Widget(self)
        self.data_list = QListWidget(self)

    def User_interface_init(self, header_structure: Dict[str, int | Dict]):
        self.header_widget.User_interface_init(header_structure)

        self.data_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.data_list.setContentsMargins(0, 0, 0, 0)
        self.data_list.setSpacing(1)

        _this_layout = QGridLayout()
        _this_layout.addWidget(self.header_widget, 0, 0)
        _this_layout.addWidget(self.data_list, 1, 0, 100, 1)
        _this_layout.addWidget(
            self.data_list.verticalScrollBar(), 0, 1, 101, 1)

        self.setLayout(_this_layout)

    def Add_widget(self, widget: QWidget):
        _place_holder = QListWidgetItem()
        _place_holder.setSizeHint(widget.sizeHint())

        self.data_list.addItem(_place_holder)
        self.data_list.setItemWidget(_place_holder, widget)

    def _Row_num_checker(self, row: int):
        if row >= 0:
            return self.__len__() if row >= self.__len__() else row
        return self.__len__() + row

    def Insert_widget(self, row: int, widget: QWidget):
        _place_holder = QListWidgetItem()
        _place_holder.setSizeHint(widget.sizeHint())

        # self.list.setMinimumWidth(
        #     round(widget.sizeHint().width() * 2)
        # )
        # self.list.setMinimumHeight(
        #     round(widget.sizeHint().height() * 21)
        # )

        self.data_list.insertItem(self._Row_num_checker(row), _place_holder)
        self.data_list.setItemWidget(_place_holder, widget)

    def Get_widget(self, row: int):
        return self.data_list.itemWidget(
            self.data_list.item(self._Row_num_checker(row))
        )

    def Scroll_to_row(self, row: int):
        _item = self.data_list.item(self._Row_num_checker(row))
        if _item is not None:
            _item.setSelected(True)
            self.data_list.scrollToItem(
                _item,
                QAbstractItemView.ScrollHint.PositionAtTop)

    def __len__(self):
        return self.data_list.count()
