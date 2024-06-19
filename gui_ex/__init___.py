from typing import List
import sys

if __package__ == "":
    # if this module call to local for another project
    from os import path

    # add file dir
    if path.dirname(path.abspath(__file__)) not in sys.path:
        sys.path.append(path.dirname(path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QWidget


@staticmethod
def Application_run(main_page: QWidget, position: List[int]):
    """ ### 어플리케이션 작동을 위한 함수
    주어진 QWidget을 시작페이지로 사용하여, 어플리케이션을 작동함.

    ------------------------------------------------------------------
    ### Args
    - `main_page`: 작동하고자 하는 어플의 시작 페이지
    - `position`: 어플의 최초 위치 및 창의 크기 -> [x, y, w, h] 순

    ### Returns
    - `process state`: 해당 어플리케이션의 종료 상태

    """
    app = QApplication(sys.argv)
    main_page.setGeometry(*position)
    main_page.show()

    return app.exec_()
