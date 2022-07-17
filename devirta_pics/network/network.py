import json
import logging
import random
import socket
import string
import threading
import time
from typing import Optional, Union

from PyQt5.QtCore import pyqtSignal, QObject
from pydantic import ValidationError

from devirta_pics.config import HOST, PORT, STATIC_PORT, STATIC_AUTH_TOKEN
from devirta_pics.network.schema import AuthReq, CommandsReq


logger = logging.getLogger(__name__)


class QNetManager(QObject):
    runCommSignal = pyqtSignal(dict)
    errorsSignal = pyqtSignal(str)

    def __init__(self, use_static=False):
        super().__init__()
        self.network = Network(self, use_static=use_static)

        self.ready = False

    @property
    def addr(self):
        return ':'.join(map(str, self.network.addr))

    @property
    def auth_token(self):
        return self.network.auth_token

    def run_comm(self, data: dict):
        self.runCommSignal.emit(data)

    def alive(self):
        return self.network.alive()

    def have_conn(self):
        return self.network.have_conn()

    def send_rdata(self, code, msg, data=None):
        self.network.send_data({'code': code, 'msg': msg, 'data': data})

    def close(self):
        self.network.close()


class Network:
    def __init__(self, manager, host=HOST, port=PORT, use_static=False):
        super().__init__()
        self.manager: QNetManager = manager

        self._closed = False
        self._thread = None

        self.conn: Optional[socket.socket] = None
        self.s_data = self.received_data = None

        if not use_static:
            self.auth_token = self.generate_token()
        else:
            self.auth_token = STATIC_AUTH_TOKEN

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind((host, port if not use_static else STATIC_PORT))
            self.socket.listen(1)
            self._open_thread()
        except socket.error as e:
            logger.error(e)
            self.close()

    @property
    def addr(self):
        if self.alive():
            return self.socket.getsockname()
        return 'АДРЕС', 'ПОРТ'

    @classmethod
    def generate_token(cls):
        symbols = list(string.ascii_uppercase + string.digits)
        return ''.join(random.sample(symbols, 6))

    def _open_thread(self):
        logger.info('SERVER STARTED')
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name='Network')
            self._thread.start()

    def _close_thread(self):
        self._closed = True
        self._thread = None
        logger.info('SERVER STOPPED')

    def _run(self):
        while not self._closed:
            if not self.socket:
                time.sleep(2)
                continue
            try:
                self.conn, addr = self.socket.accept()
                logger.info(f'NET: Connected by {addr}')
                with self.conn:
                    if self.valid_auth_data(self.read_data()):
                        while not self._closed:
                            if not (data := self.read_data()):
                                break
                            if self.valid_comm_data(data):
                                if data.get('type') == 'close':
                                    self.send_data(
                                        {'code': 200,
                                         'msg': 'Disconnected successfully.'})
                                    break
                                self.run_commands(data)
                logger.info(f'NET: Disconnected by {addr}')
            except ConnectionResetError as e:
                logger.error(e)
            except OSError:
                pass

    def read_data(self) -> Union[dict, None]:
        if self.have_conn():
            if data := self.conn.recv(1024):
                logger.debug(f'NET: New data received: {data}')
                try:
                    return json.loads(data)
                except json.decoder.JSONDecodeError:
                    return None

    def send_data(self, data: dict):
        if self.have_conn():
            logger.debug(f'NET: New data sent: {data}')
            self.conn.sendall(json.dumps(data).encode())

    def valid_auth_data(self, data: Union[dict, None]) -> bool:
        try:
            AuthReq(**(data if data is not None else {}))
        except ValidationError as e:
            self.send_data({'code': 400, 'msg': e.json()})
            logger.debug(f'NET: authentication failed: {data} |')
            return False

        if data.get('token') != self.auth_token:
            self.send_data({'code': 404, 'msg': 'Your auth-token not found.'})
            logger.debug(f'NET: authentication failed: {data} |')
            return False

        self.send_data({'code': 200, 'msg': 'Authorization is successful.'})
        logger.debug(f'NET: authentication was successful: {data} |')
        return True

    def valid_comm_data(self, data: dict) -> bool:
        try:
            CommandsReq(**(data if data is not None else {}))
        except ValidationError as e:
            self.send_data({'code': 400, 'msg': e.json()})
            logger.debug(f'NET: not valid command: {data} |')
            return False

        logger.debug(f'NET: command validation was successful: {data} |')
        return True

    def run_commands(self, data: dict):
        if self.manager.ready:
            logger.debug(f'NET: starting command: {data} |')
            self.manager.run_comm(data)
            self.send_data({'code': 200,
                            'msg': f'Starting {data.get("mode")} command...'})
        else:
            self.send_data({'code': 425,
                            'msg': 'The application is not ready yet.'})

    def have_conn(self):
        return self.conn and self.conn.fileno() != -1

    def close(self):
        self._close_thread()
        if self.socket:
            self.socket.close()

    def alive(self):
        return not self._closed
