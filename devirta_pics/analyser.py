import logging
from datetime import datetime as dt
from math import sqrt
from typing import Dict, Tuple, List, Union

import pyqtgraph as pg
import numpy as np
from PyQt5.QtCore import QTimer, pyqtSignal, QObject

from devirta_pics.utils.colors import Color
from devirta_pics.config import A_TM_DELTA, A_SMOOTH_C, G_SAVE_FD, \
    G_MAX_CHUNKS, G_UPD_FREQ, ANALYSER_LOGS, A_DELTA_TOP, A_DELTA_BOT, \
    G_SHOW_SMOOTH, G_SHOW_EXTREMES
from devirta_pics.detector import DETECTOR
from devirta_pics.utils.tools import FileManager

logger = logging.getLogger(__name__)


class Analyser(QObject):
    logsUpdatedSignal = pyqtSignal(dict)

    def __init__(self, gr_view, tm_delta=A_TM_DELTA, smooth_c=A_SMOOTH_C):
        super().__init__()
        self.graph = Graph(self, gr_view)

        self.tm_delta = tm_delta
        self.smooth_c = smooth_c  # Коэффециент сглаживания кривой

        self.graph.create_curve('asline', 'grey')
        self.graph.create_curve('bsline', 'pink')

        self.graph.create_curve('aext', 'blue', with_points=True)
        self.graph.create_curve('bext', 'cyan', with_points=True)

        self.a_delta, self.b_delta = A_DELTA_TOP, A_DELTA_BOT

        self.detected_peaks = []
        self.breath_counters = {'stomach': 0, 'chest': 0, 'mix': 0}
        self.logs = {}

        self.config_settings()

    def config_settings(self):
        if not (settings := FileManager.load_analyser_settings()):
            return
        self.tm_delta = self.convert_tm_delta(
            settings.get('time_delta', self.tm_delta))
        self.smooth_c = settings.get('smooth_c', self.smooth_c)
        self.a_delta[0] = settings.get('min_delta_top', self.a_delta[0])
        self.a_delta[1] = settings.get('max_delta_top', self.a_delta[1])
        self.b_delta[0] = settings.get('min_delta_bot', self.b_delta[0])
        self.b_delta[1] = settings.get('max_delta_bot', self.b_delta[1])

    def convert_tm_delta(self, tm_delta):
        return tm_delta // self.graph.upd_freq

    def analyse(self):
        data = self.get_analyse_data()

        # Прерываем, если данных недостаточно или обе координаты нулевые
        if data.shape[0] < self.tm_delta or \
                all(map(lambda x: x[1] == 0 and x[2] == 0, data)):
            return

        time, a_line, b_line = data[:, 0], data[:, 1], data[:, 2]

        # Сглаживаем прямые
        a_smooth, b_smooth = self.smooth_line(a_line), self.smooth_line(b_line)

        if G_SHOW_SMOOTH[0]:
            self.show_line('asline', a_smooth, time)
        if G_SHOW_SMOOTH[1]:
            self.show_line('bsline', b_smooth, time)

        self.analyse_peaks(self.find_peaks(a_smooth),
                           self.find_peaks(b_smooth), data)

    def analyse_peaks(self, a_p, b_p, data):
        if len(a_p[0]) < 3 or len(b_p[0]) < 3:
            return

        a_max_p, a_min_p = a_p[1:]
        b_max_p, b_min_p = b_p[1:]

        if len(a_max_p) > 1 and len(a_min_p) > 2:
            a_max_p, a_min_p = self.find_last_peak(a_max_p, a_min_p)
        if len(b_max_p) > 1 and len(b_min_p) > 2:
            b_max_p, b_min_p = self.find_last_peak(b_max_p, b_min_p)

        if (len(a_max_p) == 1 and len(a_min_p) == 2) and \
           (len(b_max_p) == 1 and len(b_min_p) == 2):
            # Время верхних точек всплесков
            p1_tm, p2_tm = data[a_max_p[0]][0], data[b_max_p[0]][0]

            a_max_val = data[a_max_p[0], 1]
            a_min_val = (data[a_min_p[0], 1], data[a_min_p[1], 1])

            b_max_val = data[b_max_p[0], 1]
            b_min_val = (data[b_min_p[0], 1], data[b_min_p[1], 1])

            a_delta = abs(sum(a_min_val) // 2 - a_max_val)
            b_delta = abs(sum(b_min_val) // 2 - b_max_val)

            if self.a_delta[0] <= a_delta <= self.a_delta[1] and \
                self.b_delta[0] <= b_delta <= self.b_delta[1] and \
                p1_tm not in self.detected_peaks and \
                    p2_tm not in self.detected_peaks:

                if G_SHOW_EXTREMES[0]:
                    self.show_extremes('aext', data[:, 1], a_max_p + a_min_p,
                                       data[:, 0], upd=False)
                if G_SHOW_EXTREMES[1]:
                    self.show_extremes('bext', data[:, 2], b_max_p + b_min_p,
                                       data[:, 0], upd=False)

                self.detected_peaks.extend([p1_tm, p2_tm])

                tp_br = self.determine_breathing(a_delta, b_delta)
                self.update_logs(
                    times=[p1_tm, p2_tm],
                    type_breathing=tp_br,
                    deltas=[a_delta, b_delta],
                    peaks_val=[[a_max_val, a_min_val], [b_max_val, b_min_val]]
                )

    def determine_breathing(self, a_delta, b_delta) -> str:
        if a_delta > b_delta:
            type_br = 'chest'
            self.breath_counters['chest'] += 1
        elif a_delta < b_delta:
            type_br = 'stomach'
            self.breath_counters['stomach'] += 1
        else:
            type_br = 'mix'
            self.breath_counters['mix'] += 1
        return type_br

    @classmethod
    def find_last_peak(cls, max_p, min_p):
        right = max(min_p)
        mid = sorted(filter(lambda x: x < right, max_p))[-1]
        left = sorted(filter(lambda x: x < mid, min_p))[-1]
        return [mid], [left, right]

    def get_analyse_data(self) -> np.ndarray:
        # Возвращает срех данных для анализа
        return self.graph.data_s['l'][self.graph.ptr - self.tm_delta
                                      if self.graph.ptr > self.tm_delta
                                      else 0: self.graph.ptr]

    def smooth_line(self, array: np.ndarray) -> np.ndarray:
        kernel = np.ones(self.smooth_c, dtype=float) / self.smooth_c
        return np.convolve(array, kernel, 'same')

    @staticmethod
    def find_peaks(array: np.ndarray) -> List[List[int]]:
        """
        Находит экстремумы кривой.
        :param array: Набор данных со значениями. Линейный массив.
        :return: Набор индексов экстремумов из переданного массива.
        """
        row_peaks = np.diff(np.sign(np.diff(array)))

        peaks: List[int] = row_peaks.nonzero()[0] + 1
        peaks_min: List[int] = (row_peaks > 0).nonzero()[0] + 1
        peaks_max: List[int] = (row_peaks < 0).nonzero()[0] + 1
        return [peaks, peaks_max, peaks_min]

    def show_line(self, name, line: np.ndarray, time: np.ndarray, upd=False):
        """
        Отражение на графике кривых
        """
        self.graph.set_cdata(name, np.column_stack([time, line]), upd=upd)

    def show_extremes(self, name: str, line: np.ndarray,
                      peaks: List[Union[int, float]],
                      time: np.ndarray, upd=True):

        peaks_data = np.column_stack([time, np.zeros(time.shape[0])])
        for i in peaks:
            peaks_data[i, 1] = line[i]
        self.graph.set_cdata(name, peaks_data, upd=upd)

    def update_logs(self, **kwargs):
        data = {
            'times': kwargs.get('times', None),
            'deltas': kwargs.get('deltas', None),
            'peaks_val': kwargs.get('peaks_val', None),
            'type_breathing': kwargs.get('type_breathing', None),
            'breath_counters': self.breath_counters.copy(),
        }
        self.logs.update({dt.now(): data})

        if ANALYSER_LOGS:
            logger.info(f'ANALYSER: {data}')

        self.logsUpdatedSignal.emit(data)

    def stop(self):
        self.graph.stop()


class Graph:
    def __init__(self, analyser, gr_view, max_chunks=G_MAX_CHUNKS,
                 save_fd=G_SAVE_FD, upd_freq=G_UPD_FREQ):
        self.analyser = analyser
        self.detector = DETECTOR()

        self.start_time = pg.ptime.time()

        self.plot = gr_view.addPlot()
        self.plot.setLabel('bottom', 'Time', 's')

        self.curves = {
            'A_line': self.plot.plot(pen=Color.c('white'), name='A line'),
            'B_line': self.plot.plot(pen=Color.c('red'), name='B line'),
        }

        self.max_chunks = max_chunks
        self.save_fd = save_fd
        self.upd_freq = upd_freq  # Частота с которой обновляется график
        self.config_settings()

        self.data_s = {
            'l': np.zeros((self.max_chunks, 3))
        }
        self.ptr = 0  # Указатель на последние добавленные данные

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.upd_freq)

    def config_settings(self):
        if not (settings := FileManager.load_graph_settings()):
            return
        self.save_fd = settings.get('save_full_data', self.save_fd)
        self.max_chunks = settings.get('max_chunks', self.max_chunks)
        self.upd_freq = settings.get('timer_interval', self.upd_freq)

    def create_curve(self, name, color_name, with_points=False):
        # Обект кривой
        self.curves[name] = self.plot.plot(
            pen=Color.c(color_name),
            symbol='o' if with_points else None,
            name=name
        )

    def set_cdata(self, curve_name: str, data: np.ndarray, upd=False):
        if curve_name not in self.data_s or upd:
            self.data_s[curve_name] = data
        elif not upd:
            self.data_s[curve_name] = np.concatenate(
                [self.data_s[curve_name], data])

        self.curves[curve_name].setData(x=self.data_s[curve_name][:, 0],
                                        y=self.data_s[curve_name][:, 1])

    @classmethod
    def convert_pos(cls, pos: Dict[int, Tuple[int, int]]) -> Tuple:
        """
        Конвертирует координаты 3 датчиков ABC в длины лин AB и BC
        :param pos: Координаты точек.
        :return: Длины 2 отрезков между 3 точками.
        """
        if len(pos) == 3:
            len_line_a = sqrt(abs(pos[0][0] - pos[1][0]) ** 2 +
                              abs(pos[0][1] - pos[1][1]) ** 2)
            len_line_b = sqrt(abs(pos[1][0] - pos[2][0]) ** 2 +
                              abs(pos[1][1] - pos[2][1]) ** 2)
            return len_line_a, len_line_b
        return 0, 0

    def update(self):
        now = pg.ptime.time()

        # Увеличиваем указатель
        self.ptr += 1

        # Увеличиваем размерность массива данных при переполнении
        if self.ptr >= self.data_s['l'].shape[0]:
            # # Также очищаем массив c обнаруженными пиками
            # self.analyzer.detected_peaks = self.analyzer.detected_peaks[
            #                                -self.analyzer.leave_det_peaks:]

            tmp = self.data_s['l']

            # Если не сохраняем весь массив
            if not self.save_fd:
                # Обвноялвяем массив
                self.data_s['l'] = np.zeros((self.max_chunks, 3))

                # Перемащаем в него копию последних 1/4 значений
                self.data_s['l'][:tmp.shape[0] // 4] = tmp[-tmp.shape[0] // 4:]

                # Перемещаем счетчик
                self.ptr = tmp.shape[0] // 4

                # Подрезаем остальные кривые на графике
                for k, v in self.data_s.items():
                    if k != 'l':
                        self.set_cdata(k,  v[-self.ptr:], upd=True)
            else:
                # Увеличиваем массив вдвое
                self.data_s['l'] = np.zeros((self.data_s['l'].shape[0] * 2, 3))
                self.data_s['l'][:tmp.shape[0]] = tmp

        # Указываем координату времени
        self.data_s['l'][self.ptr, 0] = now - self.start_time

        len1, len2 = self.convert_pos(self.detector.positions)

        self.data_s['l'][self.ptr, 1] = len1
        self.data_s['l'][self.ptr, 2] = len2

        self.curves['A_line'].setData(x=self.data_s['l'][:self.ptr, 0],
                                      y=self.data_s['l'][:self.ptr, 1])
        self.curves['B_line'].setData(x=self.data_s['l'][:self.ptr, 0],
                                      y=self.data_s['l'][:self.ptr, 2])
        self.analyser.analyse()

    def stop(self):
        self.timer.stop()
