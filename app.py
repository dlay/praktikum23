import sys
from PySide6.QtWidgets import QApplication

from src.mainWindow import MainWindow

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        w = MainWindow()
        w.resize(800, 600)
        w.show()
        app.exec()
    except Exception as e:
        print(f"Error: {e}")