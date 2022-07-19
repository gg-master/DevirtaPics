import json
import socket
from typing import Union

from devirta_pics.network.network import Network


class NetClient(Network):
    def __init__(self, manager, addr, req):
        self.manager = manager  # Менеджер, который реагирует на сигналы
        self.req = req  # Информация при подключении к серверу
        self.addr = addr.split(':')
        super().__init__(name=self.__class__.__name__)
        self.socket.settimeout(2.0)  # Таймаут проверки, что сокет еще открыт

    def _run(self):
        try:
            self.socket.connect((self.addr[0], int(self.addr[1])))
        except socket.error:
            self.close()
            return
        # Отправляем данные для регистрации
        self.send_data(json.loads(self.req if self.req else '{}'))
        # Если не прошли регистрацию, то закрываем соединение.
        if data := self.read_data():
            self.manager.receivedDataSignal.emit(data)
            if data.get('code') != 200:
                self.close()

        # Основной цикл для отправки команд
        while not self._closed and self.have_conn():
            if data := self.read_data():
                self.manager.receivedDataSignal.emit(data)
                if data.get('code') == '521':
                    break
        if self.alive():
            self.close()

    def read_data(self, *args) -> Union[dict, None]:
        return super().read_data(self.socket)

    def send_data(self, data: dict, *args) -> None:
        super().send_data(self.socket, data)

    def close(self) -> None:
        super().close()
