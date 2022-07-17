import sys
import time
import logging
import cv2
from PyQt5.QtWidgets import QApplication

from devirta_pics.views.main_window import MainWindow


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

logging.getLogger('PyQt5').setLevel(logging.INFO)


def exception_hook(exc_type, value, traceback):
    print(exc_type, value, traceback)
    sys._excepthook(exc_type, value, traceback)
    sys.exit(1)


class Main:
    def __init__(self):

        app = QApplication(sys.argv)

        self.main_w = MainWindow()
        self.main_w.show()

        sys.exit(app.exec())


# def main():
#     detector: NeuronDetector = NeuronDetector()
#     print('Starting main loop')
#     time.sleep(2)
#     while detector.alive():
#
#         ret, frame = detector.read()
#
#         if ret is None:
#             time.sleep(2)
#             continue
#
#         cv2.imshow('frame', frame)
#
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#
#     # After the loop release the cap object
#     detector.stop()
#     # Destroy all the windows
#     cv2.destroyAllWindows()


if __name__ == '__main__':
    sys.excepthook = exception_hook
    # main()
    Main()
