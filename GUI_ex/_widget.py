from typing import Tuple, Union, List
from enum import Enum

from PySide2.QtCore import Qt

from PySide2.QtWidgets import \
    QWidget, QSizePolicy, \
    QLayout, QGridLayout, QGroupBox, QFrame, QLabel, \
    QPushButton, QLineEdit, QComboBox, \
    QHeaderView, QTreeWidget, QTreeWidgetItem, \
    QTableWidget, QTableWidgetItem

from PySide2.QtGui import QPalette, QColor, QPixmap, QImage

# from PySide2.QtWidgets import QBoxLayout, QFormLayout, QHBoxLayout, QStackedLayout, QVBoxLayout
# from PySide2.QtWidgets import QTableWidget, QTableWidgetItem, \
#     QTreeWidget, QTreeWidgetItem, \
#     QLabel, QTextEdit
# from PySide2.QtGui import QImage, QPixmap, QColor, QKeySequence
# from PySide2.QtWidgets import QHeaderView, QSizePolicy

from python_ex._cv2 import file, Color_option
from python_ex._numpy import np_base, image, ndarray


class Param():
    class align(Enum):
        CENTER = Qt.AlignCenter
        RIGHT = Qt.AlignRight
        LEFT = Qt.AlignLeft

    class sector():
        class direction(Enum):
            VERTICAL = 0
            HORIZONTAL = 1


class sector():
    class layer():
        class grid(QGridLayout):
            def __init__(self, shape: Union[int, List[int]]) -> None:
                super().__init__()
                if isinstance(shape, int):
                    _height, _width = [shape, shape]
                elif isinstance(shape, list):
                    _height, _width = shape

                self.grid_map = np_base.get_array_from((_height, _width), is_shape=True)

            def set_contents(
                self,
                contents: Union[QWidget, QLayout, List[Union[QWidget, QLayout]]],
                position: List[Union[int, List[int]]],
                ignore_collision: bool = True
            ):
                """
                Args
                    position : [h, w], [h, w, dh, dw]
                """
                if isinstance(contents, list):
                    [self.set_contents(_content, _position) for _content, _position in zip(contents, position)]

                else:
                    if len(position) == 2:
                        _points = position  # h, w
                        _size = [1, 1]  # h, w
                    elif len(position) == 4:
                        _points = position[:2]
                        _size = [(_value if _value >= 1 else 1) for _value in position[2:]]

                    for _ct, [_point, _size_value, _limit] in enumerate(zip(_points, _size, self.grid_map.shape)):
                        _points[_ct] = (_point if _point <= _limit else _limit) if _point >= 0 else _limit - _point
                        _size[_ct] = (_limit - _points[_ct]) if _size_value > _limit - _points[_ct] else _size_value

                    is_collision = False
                    if not ignore_collision:
                        is_collision = self.grid_map[_points[0]:_points[0] + _size[0], _points[1]:_points[1] + _size[1]].sum()

                    if is_collision:
                        pass
                    else:
                        if isinstance(contents, QLayout):
                            self.addLayout(contents, _points[0], _points[1], _size[0], _size[1])

                        elif isinstance(contents, QWidget):
                            self.addWidget(contents, _points[0], _points[1], _size[0], _size[1])

                        self.grid_map[_points[0]:_points[0] + _size[0], _points[1]:_points[1] + _size[1]] += 1

    class group(QGroupBox):
        def __init__(self, name: str, default_check: bool = None, is_flat: bool = True):
            super().__init__(name)
            if default_check is not None:
                self.setCheckable(True)
                self.setChecked(default_check)

            self.draw_layout(is_flat)

        def get_layout(self) -> QLayout:
            return None

        def draw_layout(self, is_flat):
            _layout = self.get_layout()
            self.setLayout(_layout) if _layout is not None else None
            self.setFlat(is_flat)

        def set_init(self):
            pass

    class line(QFrame):
        def __init__(self, style: Param.sector.direction):
            super().__init__()
            self.setFrameShape(QFrame.HLine if style else QFrame.VLine)
            self.setFrameShadow(QFrame.Sunken)

    @staticmethod
    def contents_annotation(
        shape: Union[int, List[int]],
        annotation: List[Tuple[Union[str, QLabel], List[int]]],
        object: List[Tuple[QWidget, List[int]]]
    ) -> QGridLayout:
        _layer = sector.layer.grid(shape)

        for _contents, _position in annotation:
            _label = contents.label(_contents) if isinstance(_contents, str) else _contents
            _label.setAlignment(Param.align.CENTER.value)
            _layer.set_contents(_label, _position)

        for _contents, _position in object:
            _layer.set_contents(_contents, _position)

        return _layer


class contents():
    class custom(QWidget):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)

            self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

        def get_layout(self) -> QLayout:
            return None

        def draw_layout(self):
            _layout = self.get_layout()
            self.setLayout(_layout) if _layout is not None else None

    class label(QLabel):
        def __init__(self, label: str = None):
            super().__init__(label)
            self.setAutoFillBackground(True)

        def setBackgroundColor(self, color: List[int]):
            _palette = self.palette()
            _palette.setColor(QPalette.Window, QColor(*color))
            self.setPalette(_palette)

    class value_edit(QLineEdit):
        def __init__(self, init_text):
            super().__init__(init_text)
            self.setAutoFillBackground(True)

    class text_edit(QLineEdit):
        def __init__(self, init_text):
            super().__init__(init_text)
            self.setAutoFillBackground(True)

    class combobox(QComboBox):
        def __init__(self, init_componant: List[str] = None):
            super().__init__()
            self.addItems(init_componant) if init_componant is not None else None

    class button(QPushButton):
        def __init__(self, text: str = None) -> None:
            super().__init__(text)

    class image_module(QLabel):
        image = None

        def __init__(self, img_data: Union[str, ndarray] = None) -> None:
            super().__init__("")
            self.image_data = self.file_read(img_data) if isinstance(img_data, str) else img_data

        def file_read(self, file_dir):
            return file.image_read(file_dir, Color_option.RGB)

        def image_to_pixmap(self):  # RGB -> PIXMAP
            if self.image_data is not None:
                _h, _w, _c = self.image_data.shape
                image_format = QImage(self.image_data, _w, _h, _h * _c, QImage.Format_RGB888)
                return QPixmap.fromImage(image_format)

        def display(self, pixmap=None):
            self.setPixmap(self.image_to_pixmap() if pixmap is None else pixmap)

        def pixmap_to_image(self):
            _tmp_qimg = self.pixmap().toImage()

            _h, _w = _tmp_qimg.height(), _tmp_qimg.width()
            _format = _tmp_qimg.format()

            if _format == 4:  # QImage::Format_RGB32
                _string_img = _tmp_qimg.bits().asstring(_w * _h * 4)
                _restore_img = image.string_to_img(_string_img, _h, _w, 4)

            return _restore_img

        def image_process(self):
            pass

    class tree_module(QTreeWidget):
        def __init__(self, header_text):
            super().__init__()
            self.refresh(row=0, header=header_text)

        def refresh(self, row, header=None):
            if header is not None:
                # when use table init
                self.clear()
                self.setHeaderLabels(header)
                self.header().setStretchLastSection(False)
                self.header().setSectionResizeMode(QHeaderView.Stretch)
            else:
                # when use table clear
                self.clearContents()

        def data_insert(self, parent_widget, texts):
            _item = QTreeWidgetItem(parent_widget)

            for _ct, text in enumerate(texts):
                _item.setText(_ct, text)

            return _item

        def data_location(self, selected_item):
            def salmon(item, location_list):
                _p = item.parent()
                if _p is not None:
                    for _ct_ct in range(_p.childCount()):
                        if item == _p.child(_ct_ct):
                            location_list.append(_ct_ct)
                            break
                    _top_p = salmon(_p, location_list)
                    return _top_p
                else:
                    return item

            _location = []
            _selected_top_item = salmon(selected_item, _location)

            for _item_ct in range(self.topLevelItemCount()):
                if _selected_top_item == self.topLevelItem(_item_ct):
                    _location.append(_item_ct)
                    break
            _location.reverse()
            return _location

        def location_to_data(self, location):
            _item = self.topLevelItem(location[0])
            if len(location) > 1:
                for _index in location[1:]:
                    _item = _item.child(_index)

            return _item

    class table_module(QTableWidget):
        def __init__(self, row_count, header_text: List[str] = None,):
            super().__init__()
            self.refresh(row_count=row_count, header=header_text)

        def refresh(self, row_count: int = 0, header: List[str] = None):
            if header is not None:
                # when use table init
                self.clear()
                self.setColumnCount(len(header))
                self.setHorizontalHeaderLabels(header)
                self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
            else:
                # when use table clear
                self.clearContents()

            self.setRowCount(row_count)

        def data_insert(self, row_ct, col_ct, text):
            self.setItem(row_ct, col_ct, QTableWidgetItem(text))

        def get_selected_row_list(self, not_selected_is_all=True):
            tmp_list = list(self.selectionModel().selection())
            return_list = []

            if len(tmp_list):
                for _range_data in tmp_list:
                    _top = _range_data.top()
                    _bottom = _range_data.bottom() + 1
                    for _tmp_ct in range(_top, _bottom):
                        return_list.append(_tmp_ct)
            elif not_selected_is_all:
                for _ct in range(self.rowCount()):
                    return_list.append(_ct)

            return return_list


# class custom_module():

#     @staticmethod  # in later check it again (about structure, annotation...)
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

#     @staticmethod
#     class image_module(QLabel):
#         image = None
#         padding = 0

#         def __init__(self, padding=0) -> None:
#             super().__init__("")
#             self.padding = padding

#         def set_image(self, image_file):  # image_file -> RGB image
#             self.image = _cv2.file.image_read(image_file, _cv2.Color_option.RGB)

#         def image_to_pixmap(self):  # RGB -> PIXMAP
#             if self.image is not None:
#                 _pad_image = _cv2.draw._padding(self.image, self.padding)
#                 _h, _w, _c = _pad_image.shape
#                 image_format = QImage(_pad_image, _w, _h, _h * _c, QImage.Format_RGB888)
#                 return QPixmap.fromImage(image_format)
#             else:
#                 interface.call_message_box(
#                     title="error",
#                     message="Awaken some ERROR, When read image data. Please check it.",
#                     icon_flag="critical",
#                     bt_flags="OK")

#         def display(self, pixmap=None):
#             self.setPixmap(self.image_to_pixmap() if pixmap is None else pixmap)

#         def get_image(self):
#             _tmp_qimg = self.pixmap().toImage()

#             _h, _w = _tmp_qimg.height(), _tmp_qimg.width()
#             _format = _tmp_qimg.format()

#             if _format == 4:  # QImage::Format_RGB32
#                 _string_img = _tmp_qimg.bits().asstring(_w * _h * 4)
#                 _restore_img = _numpy.base_process.string_to_img(_string_img, _h, _w, 4)

#             return _cv2.draw._unpadding(_restore_img, self.padding)

#     @staticmethod
#     class canvas_module(image_module):
#         pen_toruch = pyqtSignal()
#         under_iamge = None
#         shape = None
#         canvas = _cv2.draw.canvas()

#         def __init__(self):
#             super().__init__("")
#             self.padding = 20
#             self.setMouseTracking(True)
#             self._draw_flag = "Polygon"

#             # QShortcut(QKeySequence(Qt.Key_C), self, activated=self._polygon_close)

#         def set_option(self, flag, **kwarg):
#             self._draw_flag = flag
#             for _data in kwarg.keys():
#                 if _data == "color":
#                     _b = kwarg[_data][0]
#                     _g = kwarg[_data][1]
#                     _r = kwarg[_data][2]
#                     self._pen_info[_data] = QColor(_r, _g, _b)

#                 elif _data == "line_style":
#                     self._pen_info[_data] = _DRAW_LINE[kwarg[_data]]

#                 elif _data in self._pen_info.keys():
#                     self._pen_info[_data] = kwarg[_data]

#         def _polygon_close(self):
#             if self._draw_flag == "Polygon" and len(self._past_x) >= 2:
#                 self._past_x.append(self._past_x[0])
#                 self._past_y.append(self._past_y[0])

#                 _, draw_image = self._draw()

#                 self._draw_data.append({
#                     "style": self._draw_flag,
#                     "x": self._past_x,
#                     "y": self._past_y})
#                 self.pen_toruch.emit()
#                 self._past_x = []
#                 self._past_y = []

#                 self.set_image(draw_image)
#                 self.image_np_data = self.get_image()[:, :, :3]

#         def _draw(self, flag=None):
#             is_end = False
#             _img = self._make_pixmap()
#             if len(self._past_x):
#                 _painter = QPainter(_img)
#                 _painter.setPen(
#                     QPen(self._pen_info["color"], self._pen_info["thick"], self._pen_info["line_style"])
#                 )

#                 _draw_option = flag if flag is not None else self._draw_flag

#                 # draw line
#                 if _draw_option == "Line":
#                     if len(self._past_x) == 1:  # preview
#                         _p1_x = self._past_x[0]
#                         _p1_y = self._past_y[0]

#                         _p2_x = self._present_x if self._present_x is not None else 0
#                         _p2_y = self._present_y if self._present_y is not None else 0

#                     elif len(self._past_x) == 2:  # draw
#                         _p1_x = self._past_x[0]
#                         _p1_y = self._past_y[0]

#                         _p2_x = self._past_x[1]
#                         _p2_y = self._past_y[1]

#                         is_end = True

#                     _painter.drawLine(_p1_x, _p1_y, _p2_x, _p2_y)

#                 # draw polygon
#                 elif _draw_option == "Polygon":
#                     if len(self._past_x) == 3:
#                         _start = [self._past_x[0], self._past_y[0]]
#                         _end = [self._past_x[-1], self._past_y[-1]]
#                         is_end = _start == _end

#                     if is_end:
#                         _xs = self._past_x
#                         _ys = self._past_y

#                     else:
#                         _tmp_x = self._present_x if self._present_x is not None else 0
#                         _tmp_y = self._present_y if self._present_y is not None else 0

#                         _xs = self._past_x + [_tmp_x, ]
#                         _ys = self._past_y + [_tmp_y, ]

#                     _st_x = _xs[0]
#                     _st_y = _ys[0]

#                     for [_x, _y] in zip(_xs[1:], _ys[1:]):
#                         _painter.drawLine(_st_x, _st_y, _x, _y)
#                         _st_x = _x
#                         _st_y = _y

#                 # draw retangle
#                 elif _draw_option == "Rectan":
#                     if len(self._past_x) == 1:  # preview
#                         _p1_x = self._past_x[0]
#                         _p1_y = self._past_y[0]

#                         _p2_x = self._present_x if self._present_x is not None else 0
#                         _p2_y = self._present_y if self._present_y is not None else 0

#                     elif len(self._past_x) == 2:  # draw
#                         _p1_x = self._past_x[0]
#                         _p1_y = self._past_y[0]

#                         _p2_x = self._past_x[1]
#                         _p2_y = self._past_y[1]

#                         is_end = True

#                     _left = min(_p1_x, _p2_x)
#                     _right = max(_p1_x, _p2_x)

#                     _top = min(_p1_y, _p2_y)
#                     _bottom = max(_p1_y, _p2_y)

#                     _painter.drawLine(_left, _top, _right, _top)
#                     _painter.drawLine(_right, _top, _right, _bottom)
#                     _painter.drawLine(_right, _bottom, _left, _bottom)
#                     _painter.drawLine(_left, _bottom, _left, _top)

#                 # draw circle
#                 elif _draw_option == "Circle":
#                     if len(self._past_x) == 1:  # preview
#                         _p1_x = self._past_x[0]
#                         _p1_y = self._past_y[0]

#                         _p2_x = self._present_x
#                         _p2_y = self._present_y

#                     elif len(self._past_x) == 2:  # draw
#                         _p1_x = self._past_x[0]
#                         _p1_y = self._past_y[0]

#                         _p2_x = self._past_x[1]
#                         _p2_y = self._past_y[1]

#                         is_end = True

#                     _R_x = abs(_p1_x - _p2_x)
#                     _R_y = abs(_p1_y - _p2_y)

#                     _painter.drawEllipse(_p1_x - _R_x, _p1_y - _R_y, 2 * _R_x, 2 * _R_y)

#                 _painter.end()

#             return is_end, QPixmap(_img)

#         def mousePressEvent(self, QMouseEvent):
#             # make draw data
#             if QMouseEvent.button() == Qt.LeftButton:
#                 self._past_x.append(self._present_x if self._present_x is not None else 0)
#                 self._past_y.append(self._present_y if self._present_y is not None else 0)

#             elif QMouseEvent.button() == Qt.RightButton:
#                 if len(self._past_x):
#                     self._past_x.pop()
#                     self._past_y.pop()

#             is_end, draw_image = self._draw()
#             self.set_image(draw_image)

#             if is_end:
#                 self._draw_data.append({
#                     "style": self._draw_flag,
#                     "x": self._past_x,
#                     "y": self._past_y})
#                 self.pen_toruch.emit()
#                 self._past_x = []
#                 self._past_y = []

#                 self._present_x = None
#                 self._present_y = None

#                 self.image_np_data = self.get_image()[:, :, :3]

#         def mouseMoveEvent(self, event):
#             # make preview data
#             self._present_x = event.x()
#             self._present_y = event.y()

#             # make preview
#             _, draw_image = self._draw()
#             self.set_image(draw_image)

#         def draw_info_clear(self):
#             self._past_x = []
#             self._past_y = []

#             self._present_x = None
#             self._present_y = None

#             self._draw_data = []

#             self._draw_flag = "Polygon"
#             self._pen_info = {
#                 "color": QColor(0x00, 0x00, 0x00),
#                 "thick": 3,
#                 "line_style": Qt.SolidLine
#             }
