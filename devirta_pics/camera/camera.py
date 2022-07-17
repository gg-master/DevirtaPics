import threading
import logging
import cv2

from devirta_pics.config import FPS, FRAME_WIDTH, FRAME_HEIGHT
from devirta_pics.utils.singleton import Singleton


logger = logging.getLogger(__name__)


class Camera(metaclass=Singleton):
    """
    Класс, который соединяется с камерой через инструменты openCV.
    Параметры fps, frame_width, frame_height - будут установлены для
    устройства, если устройство поддерживает данные параметры.
    """

    def __init__(self, fps=FPS, fr_width=FRAME_WIDTH, fr_height=FRAME_HEIGHT):
        self.fps = fps
        self.frame_width, self.frame_height = fr_width, fr_height

        self.cap = self.last_frame = self.ret = None
        self.is_restarted = False

        self._thread = None

        self.start()

    def _open_thread(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name='Camera')
            self._thread.start()

    def _close_thread(self):
        try:
            if self._thread is not None:
                self._thread.do_run = False
                self._thread.join()
        except RuntimeError:
            self._thread = None

    def _release(self):
        if self.cap is not None:
            self.cap.release()
            logger.info('DISCONNECTING CAMERA')

    def _run(self):
        while getattr(self._thread, "do_run", True) and self.alive():
            self.ret, self.last_frame = self.cap.read()
            if not self.ret:
                logger.warning('Cant read camera device. Check that the camera'
                               ' is not being used by another application. \n')
                self.stop()

    def stop(self):
        self._close_thread()
        self._release()

    def start(self):
        logger.info('STARTING CAMERA...')
        self.cap = cv2.VideoCapture(0)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        self._open_thread()

    def restart(self):
        if not self.is_restarted:
            self.is_restarted = True
            self.stop()
            self.start()
            self.is_restarted = False

    def read(self):
        return self.ret, self.last_frame

    def alive(self):
        return self.cap.isOpened() or self.is_restarted
