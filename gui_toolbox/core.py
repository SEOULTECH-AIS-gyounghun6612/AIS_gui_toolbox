from PySide6.QtWidgets import QMainWindow


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

    def __Initialize_interface__(self, **kwarg):
        raise NotImplementedError

    def __Initialize_data__(self, **kwarg):
        raise NotImplementedError

    def Run(self):
        raise NotImplementedError
    
    def Stop(self):
        raise NotImplementedError
