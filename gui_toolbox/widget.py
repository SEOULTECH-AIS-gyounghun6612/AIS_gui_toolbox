from __future__ import annotations

import numpy as np

from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Signal  # , Qt

from PySide6.QtWidgets import (QFrame, QLabel, QWidget)
# from PySide6.QtWebEngineWidgets import QWebEngineView


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
