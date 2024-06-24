from typing import Tuple, List
from enum import Enum

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget, QSizePolicy,
    QLayout, QGridLayout, QGroupBox, QFrame, QLabel,
    QPushButton, QLineEdit, QComboBox,
    QHeaderView, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem
)

from PySide6.QtGui import QPixmap, QImage
import numpy as np

from python_ex.vision import File_IO, Vision_Toolbox, Convert_Flag

from .window import Interaction_Dialog, Message_Box_Flag


class Align(Enum):
    CENTER = Qt.AlignmentFlag.AlignCenter
    RIGHT = Qt.AlignmentFlag.AlignRight
    LEFT = Qt.AlignmentFlag.AlignLeft


class Window():
    class Main_Page(QMainWindow):
        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)

    class Sub_Page(QWidget):
        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)


class Custom_Widget():
    @staticmethod
    def Attach_label(
        widget: QWidget,
        text: str,
        is_horizental: bool,
        is_widget_first: bool = False
    ):
        ...

    @staticmethod
    def Widget_grouping(
        widget: QWidget,
        text: str,
        is_horizental: bool,
        is_widget_first: bool = False
    ):
        ...

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
        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)

    class Mulit_Head_List_Widget(QWidget):
        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)


# class sector():
#     class layer():
#         class grid(QGridLayout):
#             def __init__(self, shape: Union[int, List[int]]) -> None:
#                 super().__init__()
#                 if isinstance(shape, int):
#                     _height, _width = [shape, shape]
#                 elif isinstance(shape, list):
#                     _height, _width = shape

#                 self.grid_map = np_base.get_array_from((_height, _width), is_shape=True)

#             def set_contents(
#                 self,
#                 contents: Union[QWidget, QLayout, List[Union[QWidget, QLayout]]],
#                 position: List[Union[int, List[int]]],
#                 ignore_collision: bool = True
#             ):
#                 """
#                 Args
#                     position : [h, w], [h, w, dh, dw]
#                 """
#                 if isinstance(contents, list):
#                     [self.set_contents(_content, _position) for _content, _position in zip(contents, position)]

#                 else:
#                     if len(position) == 2:
#                         _points = position  # h, w
#                         _size = [1, 1]  # h, w
#                     elif len(position) == 4:
#                         _points = position[:2]
#                         _size = [(_value if _value >= 1 else 1) for _value in position[2:]]

#                     for _ct, [_point, _size_value, _limit] in enumerate(zip(_points, _size, self.grid_map.shape)):
#                         _points[_ct] = (_point if _point <= _limit else _limit) if _point >= 0 else _limit - _point
#                         _size[_ct] = (_limit - _points[_ct]) if _size_value > _limit - _points[_ct] else _size_value

#                     is_collision = False
#                     if not ignore_collision:
#                         is_collision = self.grid_map[_points[0]:_points[0] + _size[0], _points[1]:_points[1] + _size[1]].sum()

#                     if is_collision:
#                         pass
#                     else:
#                         if isinstance(contents, QLayout):
#                             self.addLayout(contents, _points[0], _points[1], _size[0], _size[1])

#                         elif isinstance(contents, QWidget):
#                             self.addWidget(contents, _points[0], _points[1], _size[0], _size[1])

#                         self.grid_map[_points[0]:_points[0] + _size[0], _points[1]:_points[1] + _size[1]] += 1

#     class group(QGroupBox):
#         def __init__(self, name: str, default_check: bool = None, is_flat: bool = True):
#             super().__init__(name)
#             if default_check is not None:
#                 self.setCheckable(True)
#                 self.setChecked(default_check)

#             self.draw_layout(is_flat)

#         def get_layout(self) -> QLayout:
#             return None

#         def draw_layout(self, is_flat):
#             _layout = self.get_layout()
#             self.setLayout(_layout) if _layout is not None else None
#             self.setFlat(is_flat)

#         def set_init(self):
#             pass

#     class line(QFrame):
#         def __init__(self, style: Param.Sector.Direction):
#             super().__init__()
#             self.setFrameShape(
#                 QFrame.Shape.HLine if style else QFrame.Shape.VLine)
#             # self.setFrameShadow(QFrame.Sunken)

#     @staticmethod
#     def contents_annotation(
#         shape: Union[int, List[int]],
#         annotation: List[Tuple[Union[str, QLabel], List[int]]],
#         object: List[Tuple[QWidget, List[int]]]
#     ) -> QGridLayout:
#         _layer = sector.layer.grid(shape)

#         for _contents, _position in annotation:
#             _label = contents.label(_contents) if isinstance(_contents, str) else _contents
#             _label.setAlignment(Param.Align.CENTER.value)
#             _layer.set_contents(_label, _position)

#         for _contents, _position in object:
#             _layer.set_contents(_contents, _position)

#         return _layer


# class contents():
#     class tree_module(QTreeWidget):
#         def __init__(self, header_text):
#             super().__init__()
#             self.refresh(row=0, header=header_text)

#         def refresh(self, row, header=None):
#             if header is not None:
#                 # when use table init
#                 self.clear()
#                 self.setHeaderLabels(header)
#                 self.header().setStretchLastSection(False)
#                 self.header().setSectionResizeMode(QHeaderView.Stretch)
#             else:
#                 # when use table clear
#                 self.clearContents()

#         def data_insert(self, parent_widget, texts):
#             _item = QTreeWidgetItem(parent_widget)

#             for _ct, text in enumerate(texts):
#                 _item.setText(_ct, text)

#             return _item

#         def data_location(self, selected_item):
#             def salmon(item, location_list):
#                 _p = item.parent()
#                 if _p is not None:
#                     for _ct_ct in range(_p.childCount()):
#                         if item == _p.child(_ct_ct):
#                             location_list.append(_ct_ct)
#                             break
#                     _top_p = salmon(_p, location_list)
#                     return _top_p
#                 else:
#                     return item

#             _location = []
#             _selected_top_item = salmon(selected_item, _location)

#             for _item_ct in range(self.topLevelItemCount()):
#                 if _selected_top_item == self.topLevelItem(_item_ct):
#                     _location.append(_item_ct)
#                     break
#             _location.reverse()
#             return _location

#         def location_to_data(self, location):
#             _item = self.topLevelItem(location[0])
#             if len(location) > 1:
#                 for _index in location[1:]:
#                     _item = _item.child(_index)

#             return _item

#     class table_module(QTableWidget):
#         def __init__(self, row_count, header_text: List[str] = None,):
#             super().__init__()
#             self.refresh(row_count=row_count, header=header_text)

#         def refresh(self, row_count: int = 0, header: List[str] = None):
#             if header is not None:
#                 # when use table init
#                 self.clear()
#                 self.setColumnCount(len(header))
#                 self.setHorizontalHeaderLabels(header)
#                 self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
#                 self.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
#             else:
#                 # when use table clear
#                 self.clearContents()

#             self.setRowCount(row_count)

#         def data_insert(self, row_ct, col_ct, text):
#             self.setItem(row_ct, col_ct, QTableWidgetItem(text))

#         def get_selected_row_list(self, not_selected_is_all=True):
#             tmp_list = list(self.selectionModel().selection())
#             return_list = []

#             if len(tmp_list):
#                 for _range_data in tmp_list:
#                     _top = _range_data.top()
#                     _bottom = _range_data.bottom() + 1
#                     for _tmp_ct in range(_top, _bottom):
#                         return_list.append(_tmp_ct)
#             elif not_selected_is_all:
#                 for _ct in range(self.rowCount()):
#                     return_list.append(_ct)

#             return return_list
