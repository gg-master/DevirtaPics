import json
import logging
import sys

from PyQt5 import QtGui, uic
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication, QWidget

from devirta_pics.network.qnetmanager import QNetClientManager

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

logging.getLogger('PyQt5').setLevel(logging.INFO)


def exception_hook(exc_type, value, traceback):
    print(exc_type, value, traceback)
    sys._excepthook(exc_type, value, traceback)
    sys.exit(1)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('./ui/window.ui', self)
        self.net_man = None
        self.send_btn.clicked.connect(self.send_msg)
        self.connect_btn.clicked.connect(self.connect2server)

    def connect2server(self):
        if not self.net_man or not self.net_man.alive() or \
                not self.net_man.have_conn():
            self.net_man = QNetClientManager(self.addr.text(),
                                             self.req_label.toPlainText())

        self.net_man.receivedDataSignal.connect(self.set_recv_data)

    def send_msg(self):
        if self.net_man:
            if text := self.req_label.toPlainText():
                self.net_man.send_data(data=json.loads(text))

    @pyqtSlot(dict)
    def set_recv_data(self, data):
        self.resp_label.setPlainText(str(data))

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.net_man:
            self.net_man.close()
        super().closeEvent(a0)


def main():
    app = QApplication(sys.argv)

    main_w = MainWindow()
    main_w.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    sys.excepthook = exception_hook
    main()
