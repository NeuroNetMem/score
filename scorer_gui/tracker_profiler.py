# a simplified UI for testing/profiling of animal tracking

from PyQt5 import QtCore
#from PyQt5 import QtGui
from PyQt5 import QtWidgets
import logging

from scorer_gui.cv_video_widget import CVVideoWidget
from scorer_gui.obj_scorer_model import VideoDeviceManager


class ProfilerMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        flags_ = QtCore.Qt.WindowFlags()
        super(ProfilerMainWindow, self).__init__(flags=flags_)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setSizePolicy(sizePolicy)
        self.cameraWidget = CVVideoWidget(self)
        self.setMinimumSize(550, 450)
        video_filename = '/Users/fpbatta/Data/obj_test/mouse_training_OS_5trials_inteldis_23_27animals_t0001_raw.avi'
        background_frame = 97
        add_animal_frame = 446
        animal_start = (443, 17)
        animal_end = (419, 21)
        self.device = VideoDeviceManager(video_file=video_filename)
        self.cameraWidget.set_device(self.device)
        self.device.acquire_background(background_frame)
        self.device.add_animal(animal_start, animal_end, add_animal_frame)
        self.device.start_acquisition()


def _main():
    import sys
    app = QtWidgets.QApplication(sys.argv)

    window = ProfilerMainWindow()
    # window.device = CameraDevice(mirrored=True)
    window.show()
    app.quitOnLastWindowClosed = False
    # noinspection PyUnresolvedReferences
    app.exec_()


if __name__ == '__main__':
    logging.basicConfig(filename='scorer_log.log', level=logging.DEBUG)
    _main()
