import time
from threading import Thread

import cv2
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QLabel


class WindowCamera(QObject):
    changePixmap = pyqtSignal(QImage)

    def __init__(self, label: QLabel, img_src):
        super().__init__(parent=None)

        # Лэйбл, на котором будет отображаться картинка
        self.label = label
        # Источник картинки
        self.img_src = img_src

    def to_qt_format(self, img):
        # Переводим в формат для qt
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(rgb_img.data, w, h, bytes_per_line,
                                      QImage.Format_RGB888)
        try:
            # Мастшабируем в соответствии с размерами экрана
            p = convert_to_qt_format.scaled(
                self.label.width(), self.label.height(),
                Qt.KeepAspectRatio)
            # Вызываем событие об обновлении картинки
            self.changePixmap.emit(p)
        except Exception:
            pass


class CallbackCam(WindowCamera):
    def __init__(self, label: QLabel, image_src):
        super().__init__(label, image_src)

        # Подключаем коллбек
        self.img_src.connect_listener(self.to_qt_format)


class LoopCam(WindowCamera, Thread):
    def __init__(self, parent, label: QLabel, image_src):
        self.is_run = True
        self.start_time = time.time()
        self.one_second_timer = time.time()
        self.fps = 30
        self.fps_count = 0

        WindowCamera.__init__(self, label, image_src)
        Thread.__init__(self)
        Thread.start(self)

    def stop(self):
        self.is_run = False
        self.join()

    def run(self):
        # Пока камера работает получаем изображение и отображаем его
        while self.img_src.alive() and self.label and self.is_run:
            # Считывание изображения
            ret, img = self.img_src.read()

            if not ret:
                time.sleep(2)
                continue

            if time.time() - self.start_time >= 1 / self.fps:
                self.start_time = time.time()
                self.fps_count += 1

                # Получаем картикну с отмеченными распознанными объектами
                super().to_qt_format(img)

            if time.time() - self.one_second_timer >= 1:
                self.one_second_timer = time.time()
                self.fps_count = 0

