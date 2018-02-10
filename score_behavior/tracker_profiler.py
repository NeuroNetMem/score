# a simplified UI for testing/profiling of animal tracking

from PyQt5 import QtCore
from PyQt5 import QtWidgets
import logging

from score_behavior.cv_video_widget import CVVideoWidget
from score_behavior.score_controller import VideoDeviceManager
from score_behavior.ObjectSpace.analyzer import ObjectSpaceFrameAnalyzer


class ProfilerMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        flags_ = QtCore.Qt.WindowFlags()
        super(ProfilerMainWindow, self).__init__(flags=flags_)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setSizePolicy(sizePolicy)
        self.cameraWidget = CVVideoWidget(self)
        self.setMinimumSize(550, 450)

        # add_animal_frame = 859
        # animal_start = (124, 331)
        # animal_end = (110, 339)

        video_filename = '/Users/fpbatta/Data/obj_test/mouse_training_OS_5trials_inteldis_23_27animals_t0001_raw.avi'
        # start (438, 20), end (416, 19) at frame 439
        background_frame = 97
        add_animal_frame = 439
        animal_start = (438, 20)
        animal_end = (416, 19)

        # video_filename = '/Users/fpbatta/Data/obj_test/mouse_training_OS_5trials_inteldis_23_27animals_t0004_raw.avi'
        # background_frame = 90
        # add_animal_frame = 200
        # animal_start = (90, 34)
        # animal_end = (75, 31)
        self.device = VideoDeviceManager(video_file=video_filename)
        self.analyzer = ObjectSpaceFrameAnalyzer(self.device, parent=self)
        self.analyzer.init_tracker(self.device.frame_size)
        self.device.set_analyzer(self.analyzer)
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
    logging.basicConfig(filename='tracker_log.log', level=logging.DEBUG, filemode='w')
    _main()
