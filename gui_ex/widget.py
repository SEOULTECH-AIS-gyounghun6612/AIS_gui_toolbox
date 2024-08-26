from enum import Enum

from PySide6.QtCore import Qt, QDateTime

from PySide6.QtWidgets import (
    QLayout, QGridLayout, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QFrame, QListWidget,
    QTableWidget, QHeaderView, QTableWidgetItem,
    QListWidgetItem, QAbstractItemView,
)

from PySide6.QtGui import QPixmap, QImage
import numpy as np

from python_ex.system import Time, datetime
from python_ex.vision import File_IO, Vision_Toolbox, Convert_Flag

from .window import Interaction_Dialog, Message_Box_Flag


class Flag():
    class Align(Enum):
        CENTER = Qt.AlignmentFlag.AlignCenter
        RIGHT = Qt.AlignmentFlag.AlignRight
        LEFT = Qt.AlignmentFlag.AlignLeft

    class Resize(Enum):
        RESIZE_TO_CONTENTS = QHeaderView.ResizeMode.ResizeToContents
        STRETCH = QHeaderView.ResizeMode.Stretch


class Utils():
    @staticmethod
    def Make_group(
        ui_obj: list[QWidget | QLayout],
        is_horizontal: bool,
        align: Flag.Align | list[Flag.Align] | None = None
    ) -> QLayout:
        _is_l_align = isinstance(align, list)

        if _is_l_align and len(align) != len(ui_obj):
            raise ValueError(
                "!!! Widgets and align count is mismatch. check it !!!")

        _layout = QHBoxLayout() if is_horizontal else QVBoxLayout()
        for _ct, _obj in enumerate(ui_obj):
            if isinstance(_obj, QLayout):
                if align:
                    _align = align[_ct].value if _is_l_align else align.value
                    _layout.addLayout(_obj, _align)
                else:
                    _layout.addLayout(_obj)
            else:
                if align:
                    _align = align[_ct].value if _is_l_align else align.value
                    _layout.addWidget(_obj, _align)
                else:
                    _layout.addWidget(_obj)
        return _layout

    @staticmethod
    def Make_group_with_rate(
        ui_obj: list[QWidget | QLayout],
        rate: list[int],
        is_horizontal: bool,
        align: Flag.Align | list[Flag.Align] | None = None
    ) -> QLayout:
        _is_l_align = isinstance(align, list)
        if _is_l_align and len(align) != len(ui_obj):
            raise ValueError(
                "!!! Widgets and align count is mismatch. check it !!!")

        if len(rate) != len(ui_obj):
            raise ValueError(
                "!!! Widgets and rate count is mismatch. check it !!!")

        _layout = QGridLayout()
        _st = 0

        for _ct, (_obj, _rate) in enumerate(zip(ui_obj, rate)):
            _r, _c, _rs, _sc = (
                [0, _st, 1, _rate] if is_horizontal else [_st, 0, _rate, 1])

            if isinstance(_obj, QLayout):
                if align:
                    _align = align[_ct].value if _is_l_align else align.value
                    _layout.addLayout(_obj, _r, _c, _rs, _sc, _align)
                else:
                    _layout.addLayout(_obj, _r, _c, _rs, _sc)

            else:
                if align:
                    _align = align[_ct].value if _is_l_align else align.value
                    _layout.addWidget(_obj, _r, _c, _rs, _sc, _align)
                else:
                    _layout.addWidget(_obj, _r, _c, _rs, _sc)

            _st += _rate
        return _layout

    @staticmethod
    def Labeling(
        obj: QWidget | QLayout,
        label_text: str,
        caption_align: Flag.Align = Flag.Align.LEFT,
        is_vertical: bool = False,
        rate: int = 10,
    ):
        _layout = QGridLayout()
        _caption = QLabel(label_text)
        if is_vertical:  # vertical
            _cap_layout = QGridLayout()

            if caption_align is Flag.Align.LEFT:
                _cap_layout.addWidget(_caption, 0, 0)
                _cap_layout.addWidget(QLabel(), 0, 1, 1, 98)
            else:
                _cap_layout.addWidget(QLabel(), 0, 0, 1, 49)

                if caption_align is Flag.Align.CENTER:
                    _cap_layout.addWidget(_caption, 0, 49, 1, 1)
                    _cap_layout.addWidget(QLabel(), 0, 50, 1, 49)
                else:
                    _cap_layout.addWidget(QLabel(), 0, 49, 1, 49)
                    _cap_layout.addWidget(_caption, 0, 98, 1, 49)

            _layout.addLayout(_cap_layout, 0, 0)

            if isinstance(obj, QWidget):
                _layout.addWidget(obj, 1, 0, rate, 1)
            else:
                _layout.addLayout(obj, 1, 0, rate, 1)

        else:  # horizontal
            if caption_align is Flag.Align.LEFT:
                _layout.addWidget(_caption, 0, 0)
                if isinstance(obj, QWidget):
                    _layout.addWidget(obj, 0, 1, 1, 98)
                else:
                    _layout.addLayout(obj, 0, 1, 1, 98)
            else:
                if isinstance(obj, QWidget):
                    _layout.addWidget(obj, 0, 0, 1, 98)
                else:
                    _layout.addLayout(obj, 0, 0, 1, 98)
                _layout.addWidget(_caption, 0, 99)

        return _layout

    @staticmethod
    def Py_datetime_to_qdatetime(time: datetime):
        return QDateTime.fromString(
            Time.Make_text_from(time, "%Y-%m-%d %H:%M:%S"),
            "yyyy-MM-dd hh:mm:ss"
        )


class Custom_Widget():
    class Basement(QWidget):
        def __init__(self, parent: QWidget | None = None, **ui_config) -> None:
            super().__init__(parent)
            self.setLayout(
                self._User_interface_init(**ui_config)
            )

        def _User_interface_init(self, **ui_config) -> QLayout:
            raise NotImplementedError

    class Horizontal_Line(QFrame):
        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)
            self.setFrameShape(QFrame.Shape.HLine)
            self.setFrameShadow(QFrame.Shadow.Sunken)

    class Vertical_Line(QFrame):
        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)
            self.setFrameShape(QFrame.Shape.VLine)
            self.setFrameShadow(QFrame.Shadow.Sunken)

    class Iamge_Widget(QLabel):
        def __init__(
            self,
            parent: QWidget | None = None,
            img: np.ndarray | str | None = None
        ):
            super().__init__(parent)
            self.img, _is_img_load = self._Set_img(img, True)

            if _is_img_load:
                self.setPixmap(self._Img_to_pixmap())

        def _Set_img(
            self,
            img: np.ndarray | str | None = None,
            is_init: bool = False
        ) -> tuple[np.ndarray, bool]:
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
            elif len(_img.shape) == 3:  # color
                _img = Vision_Toolbox.Format_converter(_img)
                _format = QImage.Format.Format_RGB888
            else:  # color with a channel
                _img = Vision_Toolbox.Format_converter(
                    _img,
                    Convert_Flag.BGRA2RGBA
                )
                _format = QImage.Format.Format_RGBA8888

            _h, _w = _img.shape[:2]
            return QPixmap(QImage(_img.data, _w, _h, _format))

        def Display(self, img: np.ndarray | str | None = None):
            _img, _is_img_load = self._Set_img(img, True)

            if not _is_img_load:
                return False

            if _is_img_load:
                self.img = _img

            self.setPixmap(self._Img_to_pixmap())
            return True

    class Line_Display_Table(QTableWidget):
        def __init__(
            self,
            labels: list[str],
            policy_list: Flag.Resize | list[Flag.Resize] = Flag.Resize.STRETCH,
            use_id: bool = True,
            parent: QWidget | None = None
        ) -> None:
            super().__init__(parent)

            self.labels: list[str] = []
            self.policy_list: list[Flag.Resize] = []
            self.use_id = use_id
            if use_id:
                self.verticalHeader().hide()
            self.Set_labels(labels, policy_list, use_id)

        def Set_labels(
            self,
            labels: list[str],
            policy: Flag.Resize | list[Flag.Resize] = Flag.Resize.STRETCH,
            use_id: bool = True
        ):
            _labels: list[str] = ["id_num"] + labels if use_id else labels
            _id_po = [Flag.Resize.RESIZE_TO_CONTENTS, ]

            if isinstance(policy, list):
                _policy_list = _id_po + policy if use_id else policy
            else:
                _policy_list = [policy for _ in range(len(_labels))]
                if use_id:
                    _policy_list = _id_po + _policy_list

            self.labels: list[str] = _labels
            self.policy_list = _policy_list

            self.Set_header_label()

        def Set_header_label(self):
            _labels = self.labels
            _policy = self.policy_list

            self.setColumnCount(len(_labels))
            self.setHorizontalHeaderLabels(_labels)

            for _ct, _po in enumerate(_policy):
                self.horizontalHeader().setSectionResizeMode(_ct, _po.value)

        def Add_empty_line(
            self,
            obj_list: list[tuple[str | QWidget, Flag.Align, bool]],
            id_num: int | None = None
        ):
            _n_num = self.rowCount()
            _st_num = 0
            self.insertRow(_n_num)

            if self.use_id:
                # id_num
                _item = QTableWidgetItem(f"{id_num if id_num else _n_num}")
                _f = _item.flags() ^ Qt.ItemFlag.ItemIsEditable
                _item.setFlags(_f)
                _item.setTextAlignment(Flag.Align.CENTER.value)
                self.setItem(_n_num, _st_num, _item)
                _st_num = 1

            # else
            for _ct, (_obj, _align, _is_edit) in enumerate(obj_list):
                if isinstance(_obj, str):
                    _item = QTableWidgetItem(_obj)
                    _item.setTextAlignment(_align.value)
                    if not _is_edit:
                        _f = _item.flags() ^ Qt.ItemFlag.ItemIsEditable
                        _item.setFlags(_f)
                    self.setItem(_n_num, _ct + _st_num, _item)
                else:
                    if not _is_edit:
                        _obj.setEnabled(False)
                    self.setCellWidget(_n_num, _ct + _st_num, _obj)

        def Get_line(self, row_ct: int):
            raise NotImplementedError

        def Del_line(self):
            _pick = self.selectedRanges()
            _rm_list = []
            for _range in _pick:
                _st = _range.topRow()
                _ed = _range.bottomRow()

                if _st == _ed:
                    _rm_list.append(_st)
                else:
                    _rm_list += list(range(_st, _ed + 1))

            for _ct, _rm_row in enumerate(_rm_list):
                self.removeRow(_rm_row - _ct)

            _tb_ct = self.rowCount()

            if self.use_id:
                for _ct in range(_tb_ct):
                    self.takeItem(_ct, 0).setText(f"{_ct}")

        def Clear_all(self):
            _row_ct = self.rowCount()
            for _ct, _rm_row in enumerate(range(_row_ct)):
                self.removeRow(_rm_row - _ct)


class Multi_Head_Widget(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.depth: int = -1
        self.header: dict[tuple[int, int], tuple[str, int]] = {}

    def _Get_structure_size(
        self,
        header_structure: dict[str, int | dict[str, int | dict]],
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

        return _this_order  # in last order is header row size

    def User_interface_init(self, header_structure: dict[str, int | dict]):
        self._Get_structure_size(header_structure)

        _this_layout = QGridLayout(self)
        _this_layout.setSpacing(0)
        _this_layout.setContentsMargins(0, 0, 0, 0)
        for (_col, _row), (_name, row_span) in self.header.items():
            _col_span = self.depth - _col + 1
            _this_layout.addWidget(
                QLabel(_name), _row, _col, row_span, _col_span)

        self.setLayout(_this_layout)


class Multi_Head_List_Widget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.header_widget = Multi_Head_Widget(self)
        self.data_list = QListWidget(self)

    def User_interface_init(self, header_structure: dict[str, int | dict]):
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
