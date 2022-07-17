from datetime import timedelta
from enum import Enum
from typing import Optional

from PyQt5 import QtGui, uic
from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QWidget
from pymorphy2 import MorphAnalyzer

from devirta_pics.analyser import Analyser
from devirta_pics.camera.camera import Camera
from devirta_pics.config import LANG, G_SAVE_FD, G_MAX_CHUNKS, G_UPD_FREQ, \
    A_TM_DELTA, A_SMOOTH_C, A_DELTA_TOP, A_DELTA_BOT
from devirta_pics.detector import DETECTOR
from devirta_pics.data.settings.localization import LOCALIZATION
from devirta_pics.network.network import QNetManager
from devirta_pics.utils.tools import FileManager
from devirta_pics.views.camera_views import CallbackCam, LoopCam


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
        self.net_man: Optional[QNetManager] = None
        self.net_state_timer = None

        # Inner widgets windows
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
        self.analyser_s.triggered.connect(self.open_analayser_sw)

        # Детектор будет один благодаря паттерну Singleton
        DETECTOR()  # Запускаем детектор.

    def open_analayser_sw(self):
        self.analyser_sw = AnalyserSettingsWindow()
        self.analyser_sw.show()

    def open_graph_sw(self):
        self.graph_sw = GraphSettingsWindow()
        self.graph_sw.show()

    def open_check_cam_w(self):
        self.cam_check_w = CheckCamWindow()
        self.cam_check_w.show()

    def start_test_mode(self, **kwargs):
        if self.mode == AppModes.OFFLINE.value:
            TestingModeOffline(self, self.testing_time.time().minute()).show()
        else:
            TestingModeOnline(self, kwargs.get('time', 2)).show()

    def start_rehab_mode(self, **kwargs):
        if self.mode == AppModes.OFFLINE.value:
            RehabModeOffline(self).show()
        else:
            RehabModeOnline(self).show()

    def connect2server(self):
        if not self.net_man or not self.net_man.alive():
            self.net_man = QNetManager(use_static=self.use_static.isChecked())

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

    def run_net_commands(self, data):
        if self.mode == AppModes.ONLINE.value:
            mode = data.get('mode')
            if mode == 'test':
                self.start_test_mode(time=data.get('time', 2))
            elif mode == 'rehab':
                self.start_rehab_mode()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.mode is not None:
            DETECTOR().stop()
        if self.net_man:
            self.net_man.close()
        super().closeEvent(a0)


class GraphSettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('./data/ui/graph_sw.ui', self)
        self.save_btn.clicked.connect(self.save_data)
        self.set_data(**FileManager.load_graph_settings())

    def save_data(self):
        data = {
            'save_full_data': self.save_full_data.isChecked(),
            'max_chunks': self.max_chunks.value(),
            'timer_interval': self.timer_interval.value(),
        }
        FileManager.save_graph_settings(data)

    def set_data(self, **kwargs):
        """
        Устанавливает значения в интерфес окна
        :param kwargs: save_full_data
                       max_chunks
                       timer_interval
        :return:
        """
        self.save_full_data.setChecked(kwargs.get('save_full_data', G_SAVE_FD))
        self.max_chunks.setValue(kwargs.get('max_chunks', G_MAX_CHUNKS))
        self.timer_interval.setValue(kwargs.get('timer_interval', G_UPD_FREQ))


class AnalyserSettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('./data/ui/analyser_sw.ui', self)
        self.save_btn.clicked.connect(self.save_data)
        self.set_data(**FileManager.load_analyser_settings())

    def save_data(self):
        data = {
            'time_delta': self.time_delta.value(),
            'smooth_c': self.smooth_c.value(),
            'max_delta_top': self.max_delta_top.value(),
            'max_delta_bot': self.max_delta_bot.value(),
            'min_delta_top': self.min_delta_top.value(),
            'min_delta_bot': self.min_delta_bot.value(),
        }
        FileManager.save_analyser_settings(data)

    def set_data(self, **kwargs):
        """
        Устанавливает значения в интерфес окна
        :param kwargs: time_delta
                       smooth_c
                       max_delta_top, max_delta_bot,
                       min_delta_top, min_delta_bot
        :return:
        """
        self.time_delta.setValue(kwargs.get('time_delta', A_TM_DELTA))
        self.smooth_c.setValue(kwargs.get('smooth_c', A_SMOOTH_C))
        self.max_delta_top.setValue(kwargs.get('max_delta_top',
                                               A_DELTA_TOP[1]))
        self.max_delta_bot.setValue(kwargs.get('max_delta_bot',
                                               A_DELTA_BOT[1])),
        self.min_delta_top.setValue(kwargs.get('min_delta_top',
                                               A_DELTA_TOP[0])),
        self.min_delta_bot.setValue(kwargs.get('min_delta_bot',
                                               A_DELTA_BOT[0])),


class CheckCamWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('./data/ui/camera_check.ui', self)
        self.reconnect_cam_btn.clicked.connect(Camera().restart)

        self.cam = LoopCam(self, self.video_box, Camera())
        self.cam.changePixmap.connect(self.set_image)

    @pyqtSlot(QImage)
    def set_image(self, image: QImage) -> None:
        self.video_box.setPixmap(QPixmap.fromImage(image))

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.cam.stop()
        super().closeEvent(a0)


class ModeWindowBase(QMainWindow):
    def __init__(self, parent):
        super().__init__(parent=parent)
        uic.loadUi('./data/ui/mode_w.ui', self)

        self.detector = DETECTOR()
        self.cam = CallbackCam(self.mn_video_box, self.detector)
        self.analyser = Analyser(self.graphicsView)
        self.init_ui()

    def init_ui(self):
        self.parent().setEnabled(False)
        self.setEnabled(True)

        self.progressBar.hide()
        self.finish_btn.hide()
        self.cam.changePixmap.connect(self.set_image)
        self.analyser.logsUpdatedSignal.connect(self.update_logs)

    @pyqtSlot(QImage)
    def set_image(self, image: QImage) -> None:
        self.set_coord_in_label(self.detector.positions)
        self.mn_video_box.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot(dict)
    def update_logs(self, data: dict) -> None:
        self.br_logs.appendPlainText(f'{data}')

    def set_coord_in_label(self, positions) -> None:
        if len(positions) == 3:
            p1, p2, p3 = positions.values()
            self.x1_val.setText(str(p1[0]))
            self.x2_val.setText(str(p2[0]))
            self.x3_val.setText(str(p3[0]))
            self.y1_val.setText(str(p1[1]))
            self.y2_val.setText(str(p2[1]))
            self.y3_val.setText(str(p3[1]))

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.parent().setEnabled(True)

        for dockw in [self.logs_dockw, self.graph_dockw, self.coords_dockw]:
            if dockw.isFloating():
                dockw.close()
        self.analyser.stop()
        super().closeEvent(a0)


class TestingModeWBase(ModeWindowBase):
    def __init__(self, parent, ttime_min=2):
        self.ttime = timedelta(minutes=ttime_min)
        self.total_s = self.ttime.total_seconds()

        self.end_time = timedelta(minutes=0, seconds=0)

        self.one_s_tm = QTimer()
        self.one_s_tm.timeout.connect(self.check_ttime)
        self.one_s_tm.start(1000)

        super().__init__(parent)

    def init_ui(self):
        super().init_ui()
        self.progressBar.show()
        self.pr_bar_text.setText(self.timedelta2str(self.ttime))

    def check_ttime(self):
        self.ttime -= timedelta(seconds=1)
        self.pr_bar_text.setText(self.timedelta2str(self.ttime))
        self.progressBar.setValue(
            abs(100 - int(self.ttime.total_seconds() * 100 / self.total_s)))

        if self.ttime <= self.end_time:
            self.one_s_tm.stop()
            self.finish_testing()

    def finish_testing(self):
        self.analyser.stop()
        if any(self.analyser.breath_counters.values()):
            tp_br = sorted(self.analyser.breath_counters.keys(),
                           key=lambda x: self.analyser.breath_counters[x])[0]
            tp_br = LOCALIZATION.get(LANG, 'ru')[tp_br]
            self.parent().domin_bt_val.setText(f'"{tp_br}"')
            return tp_br
        return None

    @classmethod
    def timedelta2str(cls, tmd: timedelta) -> str:
        total_seconds = int(tmd.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)
        return f'{minutes}:{seconds}'

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.one_s_tm.stop()
        super().closeEvent(a0)


class TestingModeOffline(TestingModeWBase):
    def finish_testing(self):
        tp_breath = super().finish_testing()
        if not tp_breath:
            QMessageBox().warning(self, 'Результаты тестирования',
                                  'Нам не удалось определить ваш тип дыхания.'
                                  '\nПопробуйте снова!', QMessageBox.Ok)
        else:
            QMessageBox().information(self, 'Результаты тестирования',
                                      'Тестирование успешно завершено!\n'
                                      f'Ваш тип дыхания: {tp_breath}',
                                      QMessageBox.Ok)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        super().closeEvent(a0)
        if self.ttime > self.end_time:
            QMessageBox().warning(self, 'Тестирование прервано!',
                                  'Нам не удалось определить ваш тип дыхания.'
                                  '\nПопробуйте снова!', QMessageBox.Ok)


class TestingModeOnline(TestingModeWBase):
    def finish_testing(self):
        tp_breath = super().finish_testing()
        if not tp_breath:
            self.parent().net_man.send_rdata(
                code=204, msg='Mode completed unsuccessfully.')
        else:
            self.parent().net_man.send_rdata(
                code=201, msg='The mode is completed.',
                data={'type_breath': tp_breath})
        self.close()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        super().closeEvent(a0)
        if self.ttime > self.end_time:
            self.parent().net_man.send_rdata(code=204, msg='Mode interrupted.')


class RehabModeWBase(ModeWindowBase):
    def __init__(self, parent):
        super().__init__(parent)

    def init_ui(self):
        super().init_ui()
        self.finish_btn.show()
        self.finish_btn.clicked.connect(self.finish_rehab)

    def finish_rehab(self):
        self.analyser.stop()
        if any(self.analyser.breath_counters.values()):
            comment = MorphAnalyzer().parse('раз')[1]

            stom_count = self.analyser.breath_counters['stomach']
            stom = comment.make_agree_with_number(stom_count).word
            self.parent().stom_br_val.setText(f'{stom_count} {stom};')

            chest_count = self.analyser.breath_counters['chest']
            chest = comment.make_agree_with_number(chest_count).word
            self.parent().chest_br_val.setText(f'{chest_count} {chest};')

            mix_count = self.analyser.breath_counters['mix']
            mix = comment.make_agree_with_number(mix_count).word
            self.parent().mix_br_val.setText(f'{mix_count} {mix};')

            return stom_count, chest_count, mix_count
        return None


class RehabModeOffline(RehabModeWBase):
    def finish_rehab(self):
        br_counter = super().finish_rehab()
        if not br_counter:
            QMessageBox().warning(self, 'Результаты программы',
                                  'Нам не удалось определить ваш тип дыхания.'
                                  '\nПопробуйте снова!', QMessageBox.Ok)
        else:
            QMessageBox().information(self, 'Результаты программы',
                                      'Программа успешно завершена!\n'
                                      'Ваши результаты отображены в '
                                      'главном окне.', QMessageBox.Ok)


class RehabModeOnline(RehabModeWBase):
    def finish_rehab(self):
        br_counter = super().finish_rehab()
        if not br_counter:
            self.parent().net_man.send_rdata(
                code=204, msg='Mode completed unsuccessfully.')
        else:
            self.parent().net_man.send_rdata(
                code=201, msg='The mode is completed.',
                data={'breath_counter': br_counter})
        self.close()
