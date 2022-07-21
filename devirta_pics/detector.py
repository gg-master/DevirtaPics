import logging
import os
import sys
import threading
import time

import cv2
import numpy as np
import torch
from PIL import Image

from devirta_pics.camera.camera import Camera
from devirta_pics.config import (DETECTOR, DETECTOR_FPS, FPS, OBJECT_COUNT,
                                 PRINT_DETECTOR_FPS)
from devirta_pics.utils.colors import Color
from devirta_pics.utils.singleton import Singleton
from devirta_pics.utils.tools import abspath, load_rsc

CIRCLE_RADIUS: int = 1
TEXT_SCALE: float = 0.5


logger = logging.getLogger(__name__)


class BaseDetector:
    def __init__(self, fps=FPS, obj_count=OBJECT_COUNT):
        self.cam: Camera = Camera()
        self.obj_count = obj_count  # Количество распознаваемых объектов

        self.positions = {i: (0, 0) for i in range(obj_count)}  # {num: (x, y)}

        self.frame = None  # Кадр с отрисованными координатам
        self.fps, self.fps_count = fps, 0

        self.start_time = time.time()  # Время запуска таймера
        self.one_second_timer = time.time()

        self._thread, self.is_run = None, True

        # Слушатели, ожидающие изображения
        self._callbacks = []

        self.start()

    def connect_listener(self, callback):
        self._callbacks.append(callback)

    def start(self):
        self.is_run = True
        if self._thread is None or not self._thread.is_alive():

            # Если камера отключена, то запускаем ее
            if not self.cam.alive():
                self.cam.restart()
            logger.info('STARTING DETECTOR...')
            self._thread = threading.Thread(
                target=self._run, name='NeuronDetector')
            self._thread.start()

    def stop(self):
        if self.is_run:
            self.is_run = self._thread.do_run = False
            self._thread.join()
            self.cam.stop()

    def restart(self):
        self.stop()
        self.start()

    def alive(self):
        return self.cam.alive()

    def read(self):
        return self.frame is not None, self.frame

    def _run(self):
        pass

    def call_listeners(self, *args):
        for func in self._callbacks:
            try:
                func(*args)
            except TypeError as e:
                logger.error(e)


class NeuronDetector(BaseDetector, metaclass=Singleton):
    def __init__(self, fps=DETECTOR_FPS, obj_count=OBJECT_COUNT):
        # Загрузка сетки из корня проекта, а модели из data/neuron
        self.model = torch.hub.load(load_rsc(
            'data/neuron/ultralytics_yolov5_master'), 'custom', source='local',
            path=load_rsc('data/neuron/best.pt'))
        super().__init__(fps, obj_count)

    def _run(self) -> None:
        # Пока камера работает получаем изображение и модифицируем его
        while getattr(self._thread, "do_run", True) and self.cam.alive():
            # Считываем кадры с устаовленным fps
            if time.time() - self.start_time >= 1 / self.fps:
                # Считывание изображения
                ret, img = self.cam.read()

                if not ret:
                    continue

                self.start_time = time.time()
                self.fps_count += 1

                # Получаем картикну с отмеченными распознанными объектами
                self.frame = self._get_img_with_objects(img)
                self.call_listeners(self.frame)

            # Каждую секунду обновляем счетчик кадров
            if time.time() - self.one_second_timer >= 1:
                if PRINT_DETECTOR_FPS:
                    print(f'DETECTOR FPS: {self.fps_count}')
                self.one_second_timer = time.time()
                self.fps_count = 0

    def _get_img_with_objects(self, img):
        """
        Находит кубы на картинке и отрисовывает их на изображении.
        :param img: Image from camera device
        :return: Image with recognized objects
        """
        output = self._search(img)
        cubes_count = len(output.pandas().xyxy[0])
        positions = []
        for i in range(self.obj_count if cubes_count >= self.obj_count
                       else cubes_count):
            x_min = int(output.pandas().xyxy[0]['xmin'][i])
            x_max = int(output.pandas().xyxy[0]['xmax'][i])
            y_min = int(output.pandas().xyxy[0]['ymin'][i])
            y_max = int(output.pandas().xyxy[0]['ymax'][i])

            x = x_min + (abs(x_max - x_min) // 2)
            y = y_min + (abs(y_max - y_min) // 2)

            cv2.rectangle(img=img, pt1=(int(x_min), int(y_max)),
                          pt2=(int(x_max), int(y_min)),
                          color=(255, 0, 0), thickness=2)

            cv2.circle(img, (x, y), CIRCLE_RADIUS, Color.c('yellow'), 2)
            cv2.putText(img, f"{x}-{y}", (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, TEXT_SCALE,
                        Color.c('yellow'), 2)

            # Создаем новый список координат
            positions.append((x, y))

        # Сортируем координаты по Y и сохраняем их в словрь
        self.positions.update({k: v for k, v in enumerate(
            sorted(positions, key=lambda x: x[1]))})

        return img

    def _search(self, image_matrix):
        """
        Находит кубы на изображении
        """
        pil_image = Image.fromarray(np.uint8(image_matrix)).convert('RGB')
        output = self.model(pil_image)
        return output


try:
    DETECTOR = globals()[DETECTOR]
except KeyError:
    sys.exit('Invalid type of detector. Check config.py.')
