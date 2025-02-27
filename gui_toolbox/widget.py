from __future__ import annotations

from typing import Any, Literal
from dataclasses import InitVar, dataclass, field

import numpy as np

from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Signal  # , Qt

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QTabBar, QTabWidget, QLineEdit, QPushButton,
    QLayout, QVBoxLayout, QHBoxLayout
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from python_ex.project import Config


INTERFACE = Literal[
    "vertical", "horizontal", "label", "button", "webview"]


@dataclass
class Interface_Config(Config.Basement):
    name: str = "interface"
    element_type: INTERFACE = "label"

    size: list[int] = field(default_factory=lambda: [1, 1, 1, 1])

    # parameter when this interface is widget
    arg: dict[str, Any] | None = field(default_factory=dict)
    style: dict[str, str] = field(default_factory=dict)
    label: str | None = None
    caption: str | None = None
    event: dict[str, str] = field(default_factory=dict)

    # parameter when this interface is layout
    children: InitVar[list[dict[str, Any]] | None] = field(
        default_factory=list)
    children_cfg: list[Interface_Config] = field(default_factory=list)

    def __post_init__(self, children: list[dict[str, Any]] | None):
        if children is not None:
            self.children_cfg = [
                Interface_Config(**_args) for _args in children
            ]

    def Config_to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "element_type": self.element_type,
            "size": self.size,
            "event": self.event,
            "arg": self.arg,
            "style": self.style,
            "label": self.label,
            "caption": self.caption,
            "children": [_i.Config_to_dict() for _i in self.children_cfg]
        }


def Get_layout(
    layer_type: INTERFACE,
    interface: list[tuple[QLayout | QWidget, list[int]]]
) -> QLayout:
    if layer_type in ["vertical", "horizontal"]:
        _layout = QVBoxLayout() if layer_type == "vertical" else QHBoxLayout()
        for _i, _size in interface:
            if isinstance(_i, QWidget):
                _layout.addWidget(_i, _size[0])
            else:
                _layout.addLayout(_i, _size[0])
        return _layout
    return QVBoxLayout()


def Get_widget(cfg: Interface_Config) -> QWidget:
    _type = cfg.element_type
    _arg = (cfg.arg or {})

    if _type == "button":
        _ui = QPushButton(**_arg)
    elif _type == "webview":
        _ui = QWebEngineView(**_arg)
    else:
        _ui = QWidget()

    return _ui


class Saperate_Line(QFrame):
    def __init__(
        self,
        is_horizontal: bool,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setFrameShape(
            QFrame.Shape.HLine if is_horizontal else QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class Image_Display_Widget(QLabel):
    """
    이미지 데이터를 Pixmap으로 변환하여 표시하는 위젯.

    ### Attributes:
        is_init_fail (Signal): 이미지 변환 실패 시 신호를 발생시키는 시그널.
    """
    # signal
    is_init_fail: Signal = Signal(int)

    def Update_pixmap(self, img: np.ndarray):
        """
        NumPy 배열 이미지를 QPixmap으로 변환하여 QLabel에 표시.

        ### Args:
        img (np.ndarray): 변환할 이미지 배열 (Grayscale, RGB, RGBA 사용).

        ### Returns:
            bool: 변환 및 적용 성공 여부. 실패 시 False 반환.
        """
        if img.ndim > 3:
            self.is_init_fail.emit(1)  # input data is not image
            return False

        if img.ndim == 2:  # Grayscale
            _format = QImage.Format.Format_Grayscale8 if (
                img.dtype == np.uint8) else QImage.Format.Format_Grayscale16
        elif img.shape[2] == 3:  # RGB
            _format = QImage.Format.Format_RGB888
        elif img.shape[2] == 4:  # RGBA
            _format = QImage.Format.Format_RGBA8888
        else:
            self.is_init_fail.emit(1)  # input data is not image
            return False

        _h, _w = img.shape[:2]
        self.setPixmap(QPixmap.fromImage(QImage(img.data, _w, _h, _format)))
        return True


class Editable_TabBar(QTabBar):
    tab_name_change: Signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.name_edit = QLineEdit(self)
        self.name_edit.setVisible(False)
        self.name_edit.editingFinished.connect(self.Changed_name)
        self.current_edit_index = None

    def mouseDoubleClickEvent(self, event):
        index = self.tabAt(event.pos())
        if index < 0 or self.tabText(index) == "+":
            return
        self.current_edit_index = index

        self.name_edit.setGeometry(self.tabRect(index))
        self.name_edit.setText(self.tabText(index))
        self.name_edit.setVisible(True)
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def Changed_name(self):
        if self.current_edit_index is not None:
            new_text = self.name_edit.text()
            self.setTabText(self.current_edit_index, new_text)
        self.name_edit.setVisible(False)
        self.current_edit_index = None


class Editable_Tab(QTabWidget):
    def __init__(
        self,
        tab_prefix: str,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.tab_prefix = tab_prefix

        self.setTabBar(Editable_TabBar(self))
        self.setTabsClosable(True)

        self.addTab(QWidget(), "+")
        self.tabBar().setTabButton(
            0, QTabBar.ButtonPosition.RightSide, None)

        self.tabCloseRequested.connect(self._Close_tab)
        self.tabBarClicked.connect(self._Handle_tab_click)

    def _Make_new_tab(self, **kwarg) -> tuple[str, QWidget]:
        raise NotImplementedError

    def Add_new_tab(self, **kwarg):
        _tab_name, _tab_widget = self._Make_new_tab(**kwarg)
        _this_index = self.count() - 1  # 마지막 '+' 탭 앞에 삽입
        self.insertTab(_this_index, _tab_widget, _tab_name)
        self.setCurrentIndex(_this_index)

    def _Close_tab(self, index):
        if index == self.count() - 1:
            return
        self.removeTab(index)

    def _Handle_tab_click(self, index):
        if index == self.count() - 1:
            self.Add_new_tab()
