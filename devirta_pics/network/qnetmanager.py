from PyQt5.QtCore import QObject, pyqtSignal

from devirta_pics.network.client import NetClient
from devirta_pics.network.server import NetServer


class QNetManagerBase(QObject):
    receivedDataSignal = pyqtSignal(dict)
    errorsSignal = pyqtSignal(str)

    def __init__(self, net):
        super().__init__()
        self.net = net

    def alive(self):
        return self.net.alive()

    def have_conn(self):
        return self.net.have_conn()

    def send_data(self, **kwargs):
        self.net.send_data(kwargs.get('data'))

    def close(self):
        self.net.close()


class QNetServerManager(QNetManagerBase):
    runCommSignal = pyqtSignal(dict)

    def __init__(self, use_static=False):
        super().__init__(NetServer(self, use_static=use_static))
        self.ready = False

    @property
    def addr(self):
        return ':'.join(map(str, self.net.addr))

    @property
    def auth_token(self):
        return self.net.auth_token

    def run_comm(self, data: dict):
        self.runCommSignal.emit(data)

    def send_data(self, code, msg, **kwargs):
        super().send_data(data={'code': code, 'msg': msg, **kwargs})


class QNetClientManager(QNetManagerBase):
    def __init__(self, addr, req):
        super().__init__(NetClient(self, addr, req))
