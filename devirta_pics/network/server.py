import logging
import random
import socket
import string
import time
from typing import Mapping, Optional, Union

from pydantic import ValidationError

from devirta_pics.config import HOST, PORT, STATIC_AUTH_TOKEN, STATIC_PORT
from devirta_pics.network.network import Network
from devirta_pics.network.schema import AuthReq, CommandsReq

logger = logging.getLogger(__name__)


class NetServer(Network):
    def __init__(self, manager, host=HOST, port=PORT, use_static=False):
        self.manager = manager

        self.conn: Optional[socket.socket] = None
        self.s_data = self.received_data = None

        # Используется статичный токен
        if not use_static:
            self.auth_token = self.generate_token()
        else:
            self.auth_token = STATIC_AUTH_TOKEN

        try:
            super().__init__(name=self.__class__.__name__)
            self.socket.bind((host, port if not use_static else STATIC_PORT))
            self.socket.listen()
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

    def _run(self):
        while not self._closed:
            # Если еще не успели заупстить сокет, то ожидаем
            if not self.socket:
                time.sleep(2)
                continue
            try:
                self.conn, addr = self.socket.accept()
                self.conn.settimeout(2.0)
                logger.info(f'NET: Connected by {addr}')
                with self.conn:
                    # Аунтифицируем клиента
                    if self.valid_auth_data(self.read_data(self.conn)):
                        while not self._closed and self.have_conn():
                            if (data := self.read_data()) is None:
                                continue
                            # Если данные - это пустой словарь,
                            # то передача закончилась
                            elif not data:
                                break
                            # Валидируем команды от клиента
                            if self.valid_comm_data(data):
                                if data.get('type') == 'close':
                                    break
                                self.run_commands(data)
                    if self._closed:
                        self.send_data({'code': 521, 'msg': 'Server is Down'})
                    else:
                        self.send_data({'code': 200,
                                        'msg': 'Disconnected successfully.'})
                logger.info(f'NET: Disconnected by {addr}')
            except ConnectionResetError as e:
                logger.error(e)
                self.close()
            except OSError:
                pass

    def read_data(self, *args) -> Union[dict, None]:
        return super().read_data(self.conn)

    def send_data(self, data: dict, *args) -> None:
        return super().send_data(self.conn, data)

    def valid_auth_data(self, data: Union[dict, None]) -> bool:
        try:
            if not isinstance(data, Mapping):
                raise ValueError()
            AuthReq(**(data if data is not None else {}))
        except (ValidationError, ValueError) as e:
            err = 'Invalid command.'
            if isinstance(e, ValidationError):
                err = e.json()
            self.send_data({'code': 400, 'msg': err})
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
            if not isinstance(data, Mapping):
                raise ValueError()
            CommandsReq(**(data if data is not None else {}))
        except ValidationError as e:
            err = 'Invalid command.'
            if isinstance(e, ValidationError):
                err = e.json()
            self.send_data({'code': 400, 'msg': err})
            logger.debug(f'NET: Invalid command: {data} |')
            return False

        logger.debug(f'NET: command validation was successful: {data} |')
        return True

    def run_commands(self, data: dict) -> None:
        if self.manager.ready:
            logger.debug(f'NET: starting command: {data} |')
            self.manager.run_comm(data)
        else:
            self.send_data({'code': 425,
                            'msg': 'The application is not ready yet.'})

    def have_conn(self) -> bool:
        return self.conn and self.conn.fileno() != -1
