# import sys
# from PySide2.QtWidgets import QApplication, QWidget

# app = QApplication(sys.argv)
# window = QWidget()
# window.show()
# app.exec_()


from GUI_ex._base import Application

from test_resource.page import main_page


_app = Application([50, 50, 600, 1200])

_app.set_root_page(main_page.main("Planner"))

_app._start()
_app._end()
