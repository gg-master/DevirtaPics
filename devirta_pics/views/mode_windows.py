from datetime import timedelta

from pymorphy2 import MorphAnalyzer
from PyQt5 import QtGui, uic
from PyQt5.QtCore import QTimer, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from devirta_pics.analyser import Analyser
from devirta_pics.config import LANG, LOCALIZATION
from devirta_pics.detector import DETECTOR
from devirta_pics.utils.tools import load_rsc
from devirta_pics.views.camera_views import CallbackCam


class ModeWindowBase(QMainWindow):
    def __init__(self, parent):
        super().__init__(parent=parent)
        uic.loadUi(load_rsc('data/ui/mode_w.ui'), self)

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

    def check_ttime(self) -> None:
        # Обновляет таймер и проверяет вышло ли время
        self.ttime -= timedelta(seconds=1)
        self.pr_bar_text.setText(self.timedelta2str(self.ttime))
        self.progressBar.setValue(
            abs(100 - int(self.ttime.total_seconds() * 100 / self.total_s)))

        if self.ttime <= self.end_time:
            self.one_s_tm.stop()
            self.finish_testing()

    def finish_testing(self):
        self.analyser.stop()
        if any(val := self.analyser.breath_counters.values()) and \
                sum(val) != val[0]*len(val):
            tp_br = sorted(self.analyser.breath_counters.keys(),
                           key=lambda x: self.analyser.breath_counters[x])[0]
            self.parent().domin_bt_val.setText(
                f'"{LOCALIZATION.get(LANG, "ru")[tp_br]}"')
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
        tp_breath = LOCALIZATION.get(LANG, "ru").get(super().finish_testing())
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
            self.parent().net_man.send_data(
                code=204, msg='Mode completed unsuccessfully.', data=None)
        else:
            self.parent().net_man.send_data(
                code=201, msg='The mode is completed.',
                data={'type_breath': tp_breath})
        self.close()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        super().closeEvent(a0)
        if self.ttime > self.end_time:
            self.parent().net_man.send_data(code=204, msg='Mode interrupted.',
                                            data=None)


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

            return self.analyser.breath_counters
        return None

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        is_visible = self.isVisible()
        super().closeEvent(a0)
        if is_visible:
            self.finish_rehab()


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
            self.parent().net_man.send_data(
                code=204, msg='Mode completed unsuccessfully.', data=None)
        else:
            self.parent().net_man.send_data(
                code=201, msg='The mode is completed.',
                data={'breath_counter': br_counter})
        self.close()
