import json
import logging
import socket
import threading
from abc import ABC
from typing import Union

logger = logging.getLogger(__name__)


class Network(ABC):
    def __init__(self, name='Network'):
        self.name = name
        self._closed = False
        self._thread = None

        # Подготавливает сокет с TCP ipv4 соединения
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._open_thread()

    def _open_thread(self):
        logger.info(f'{self.name} STARTED')
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name=self.name)
            self._thread.start()

    def _close_thread(self):
        self._closed = True
        self._thread = None  # При отключении потока убираем ссылку на его
        logger.info(f'{self.name} STOPPED')

    def _run(self):
        pass

    def read_data(self, sock: socket.socket) -> Union[dict, None]:
        if self.have_conn():
            try:
                # Читаем инфу из буфера
                if data := sock.recv(1024):
                    logger.debug(f'NET: New data received: {data}')
                    try:
                        return json.loads(data)
                    except (json.decoder.JSONDecodeError, UnicodeDecodeError):
                        return None
                # Если буфер пустой, то возвращаем пустой словарь
                return {}
            except (ConnectionAbortedError, ConnectionResetError):
                # При обрыве соединения, закрываем сокет
                sock.close()
                return None
            except (socket.timeout, OSError):
                return None

    def send_data(self, sock: socket.socket, data: dict):
        if self.have_conn():
            logger.debug(f'NET: New data sent: {data}')
            sock.sendall(json.dumps(data).encode())

    def close(self):
        self._close_thread()
        if self.socket is not None:
            self.socket.close()

    def have_conn(self):
        return self.socket and self.socket.fileno() != -1

    def alive(self):
        return not self._closed
