from PyQt5 import QtGui, uic
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget

from devirta_pics.camera.camera import Camera
from devirta_pics.config import (A_DELTA_BOT, A_DELTA_TOP, A_SMOOTH_C,
                                 A_TM_DELTA, G_MAX_CHUNKS, G_SAVE_FD,
                                 G_SHOW_EXT, G_SHOW_SMOOTH, G_UPD_FREQ)
from devirta_pics.utils.tools import FileManager
from devirta_pics.views.camera_views import LoopCam


class GraphSettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('./data/ui/graph_sw.ui', self)
        self.save_btn.clicked.connect(self.save_data)
        self.set_data(**FileManager.load_graph_settings())

    def save_data(self) -> None:
        data = {
            'save_full_data': self.save_full_data.isChecked(),
            'max_chunks': self.max_chunks.value(),
            'timer_interval': self.timer_interval.value(),
            'show_sm_a': self.sh_sm_a.isChecked(),
            'show_sm_b': self.sh_sm_b.isChecked(),
            'show_ext_a': self.sh_ext_a.isChecked(),
            'show_ext_b': self.sh_ext_b.isChecked(),
        }
        FileManager.save_graph_settings(data)

    def set_data(self, **kwargs) -> None:
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
        self.sh_sm_a.setChecked(kwargs.get('show_sm_a', G_SHOW_SMOOTH[0]))
        self.sh_sm_b.setChecked(kwargs.get('show_sm_b', G_SHOW_SMOOTH[1]))
        self.sh_ext_a.setChecked(kwargs.get('show_ext_a', G_SHOW_EXT[0]))
        self.sh_ext_b.setChecked(kwargs.get('show_ext_b', G_SHOW_EXT[1]))


class AnalyserSettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('./data/ui/analyser_sw.ui', self)
        self.save_btn.clicked.connect(self.save_data)
        self.set_data(**FileManager.load_analyser_settings())

    def save_data(self) -> None:
        data = {
            'time_delta': self.time_delta.value(),
            'smooth_c': self.smooth_c.value(),
            'max_delta_top': self.max_delta_top.value(),
            'max_delta_bot': self.max_delta_bot.value(),
            'min_delta_top': self.min_delta_top.value(),
            'min_delta_bot': self.min_delta_bot.value(),
        }
        FileManager.save_analyser_settings(data)

    def set_data(self, **kwargs) -> None:
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
