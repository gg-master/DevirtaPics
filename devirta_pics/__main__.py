import logging
import sys

from PyQt5.QtWidgets import QApplication

from devirta_pics.views.main_window import MainWindow

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

logging.getLogger('PyQt5').setLevel(logging.INFO)


def exception_hook(exc_type, value, traceback):
    print(exc_type, value, traceback)
    sys._excepthook(exc_type, value, traceback)
    sys.exit(1)


def main():
    app = QApplication(sys.argv)

    main_w = MainWindow()
    main_w.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    sys.excepthook = exception_hook
    main()
