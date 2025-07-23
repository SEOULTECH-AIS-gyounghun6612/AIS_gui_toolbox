import sys

from PySide6.QtWidgets import QApplication, QMainWindow

from gui_toolbox.widget import ViewerWidget


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QMainWindow()
    viewer_widget = ViewerWidget()

    window.setCentralWidget(viewer_widget)
    window.resize(1280, 720)

    window.setWindowTitle("3D Gaussian Splatting Viewer")

    print("\n--- Controls ---")
    print("Left Mouse Drag: Rotate View")
    print("Right Mouse Drag: Pan View")
    print("Mouse Wheel: Zoom\n")

    window.show()
    sys.exit(app.exec())
