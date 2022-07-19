from enum import Enum
from typing import Optional

from PyQt5 import QtGui, uic
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow

from devirta_pics.camera.camera import Camera
from devirta_pics.detector import DETECTOR
from devirta_pics.network.qnetmanager import QNetServerManager
from devirta_pics.views.mode_windows import (ModeWindowBase, RehabModeOffline,
                                             RehabModeOnline,
                                             TestingModeOffline,
                                             TestingModeOnline)
from devirta_pics.views.settings_windows import (AnalyserSettingsWindow,
                                                 CheckCamWindow,
                                                 GraphSettingsWindow)


class AppModes(Enum):
    OFFLINE = 0
    ONLINE = 1


class ProgramModes(Enum):
    TESTING = 0
    REHAB = 1


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.mode = None
        self.net_man: Optional[QNetServerManager] = None
        self.net_state_timer = None

        # Inner widgets windows
        self.active_mode_w: Optional[ModeWindowBase] = None
        self.cam_check_w = self.graph_sw = self.analyser_sw = None

        self.load_started_w()

    def load_started_w(self):
        self.menuBar().hide()
        self.statusBar().hide()
        uic.loadUi('./data/ui/started_w.ui', self)
        self.next_btn.clicked.connect(self.load_main_w)
        self.connect_btn.clicked.connect(self.connect2server)

        self.mode = None
        if self.net_man:
            self.connect2server()
            self.net_man.ready = True

    def load_main_w(self):
        self.mode = self.tabWidget.currentIndex()
        uic.loadUi('./data/ui/mn_w.ui', self)

        self.activate_mode()

        # Init window buttons
        self.back_btn.clicked.connect(self.load_started_w)
        self.start_test_btn.clicked.connect(self.start_test_mode)
        self.start_rehab_btn.clicked.connect(self.start_rehab_mode)
        # Init menubar in window
        self.restart_cam.triggered.connect(Camera().restart)
        self.check_cam.triggered.connect(self.open_check_cam_w)
        self.graph_s.triggered.connect(self.open_graph_sw)
        self.analyser_s.triggered.connect(self.open_analyser_sw)

        # Детектор будет один благодаря паттерну Singleton
        DETECTOR()  # Запускаем детектор.

    def open_analyser_sw(self) -> None:
        self.analyser_sw = AnalyserSettingsWindow()
        self.analyser_sw.show()

    def open_graph_sw(self) -> None:
        self.graph_sw = GraphSettingsWindow()
        self.graph_sw.show()

    def open_check_cam_w(self) -> None:
        self.cam_check_w = CheckCamWindow()
        self.cam_check_w.show()

    def start_test_mode(self, **kwargs) -> None:
        if self.mode == AppModes.OFFLINE.value:
            self.active_mode_w = TestingModeOffline(
                self, self.testing_time.time().minute())
        else:
            self.active_mode_w = TestingModeOnline(self, kwargs.get('time', 2))
        self.active_mode_w.show()

    def start_rehab_mode(self) -> None:
        if self.mode == AppModes.OFFLINE.value:
            self.active_mode_w = RehabModeOffline(self)
        else:
            self.active_mode_w = RehabModeOnline(self)
        self.active_mode_w.show()

    def connect2server(self):
        if not self.net_man or not self.net_man.alive():
            self.net_man = QNetServerManager(
                use_static=self.use_static.isChecked())

        if self.net_man.alive():
            self.addr.setText(self.net_man.addr)
            self.token.setText(self.net_man.auth_token)
            self.online_info.setText('Сервер запущен')
            self.online_info.setStyleSheet('background: rgb(0, 255, 0);')
        else:
            self.online_info.setText('Статичный адрес недоступен')
            self.online_info.setStyleSheet('background: rgb(255, 170, 0);')

        self.net_man.runCommSignal.connect(self.run_net_commands)
        # self.net_man.errorsSignal.connect(self.show_net_errors)

    def activate_mode(self):
        if self.mode == AppModes.ONLINE.value:
            self.net_state_timer = QTimer()
            self.net_state_timer.timeout.connect(self.check_net_state)
            self.net_state_timer.start(50)

            self.testing_time.setEnabled(False)
            self.start_test_btn.setEnabled(False)
            self.start_rehab_btn.setEnabled(False)

            if self.net_man:
                self.net_man.ready = True

        elif self.mode == AppModes.OFFLINE.value:
            if self.net_state_timer:
                self.net_state_timer.stop()
                self.statusBar().clearMessage()

    def show_net_errors(self, error: str):
        pass
        # if self.net_state_timer:
        #     self.net_state_timer.stop()
        # self.online_info.setText(error)
        # self.online_info.setStyleSheet('background: rgb(255, 170, 0);')

    def check_net_state(self):
        stb = self.statusBar()
        if self.net_man and self.net_man.alive():
            if not self.net_man.have_conn():
                stb.setStyleSheet('background: rgb(165, 165, 165);')
                stb.showMessage('Сервер запущен. Подключений не обнаружено!')
            else:
                stb.setStyleSheet('background: rgb(0, 255, 0);')
                stb.showMessage('Сервер запущен. Подключение установлено.')
        else:
            stb.setStyleSheet('background: rgb(255, 170, 0);')
            stb.showMessage('Сервер был остановлен!')

    def run_net_commands(self, data: dict) -> None:
        if self.mode == AppModes.ONLINE.value:
            tp, mode = data.get('type'), data.get('mode')
            if tp == 'stop':
                if self.active_mode_w and self.active_mode_w.isVisible():
                    self.active_mode_w.close()
                    self.active_mode_w = None
                else:
                    self.net_man.send_data(
                        code=404, msg='Not found active mode')
                return
            # Если один из режимов уже запущен
            if self.active_mode_w and self.active_mode_w.isVisible():
                self.net_man.send_data(code=425, msg='Failed to start mode')
                return

            self.net_man.send_data(code=200, msg=f'Starting {mode} command...')
            if mode == 'test':
                self.start_test_mode(time=int(data.get('time', 2)))
            elif mode == 'rehab':
                self.start_rehab_mode()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.mode is not None:
            DETECTOR().stop()
        if self.net_man:
            self.net_man.close()
        super().closeEvent(a0)
