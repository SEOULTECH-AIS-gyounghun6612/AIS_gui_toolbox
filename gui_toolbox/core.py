from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import QTimer


POSITION = tuple[int, int, int, int]

DEFAULT_P =  (100, 100, 1600, 900)


class Main_Window(QMainWindow):
    def __init__(
        self, title: str = "Demo", position: POSITION = DEFAULT_P, **kwarg
    ):
        super().__init__(None)
        self.setWindowTitle(title)
        self.setGeometry(*position)

        self.__Initialize_data__(**kwarg)
        self.__Initialize_interface__(**kwarg)

    def showEvent(self, event):
        """윈도우가 표시된 후 GL 초기화가 완료될 시간을 확보하기 위해 타이머 사용."""
        super().showEvent(event)
        QTimer.singleShot(0, self.Run)

    def __Initialize_interface__(self, **kwarg):
        raise NotImplementedError

    def __Initialize_data__(self, **kwarg):
        raise NotImplementedError

    def Run(self):
        raise NotImplementedError
    
    def Stop(self):
        raise NotImplementedError
