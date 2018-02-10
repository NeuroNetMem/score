from .tracking.tracker import Tracker
import cv2
from PyQt5 import QtCore
import logging
logger = logging.getLogger(__name__)


class FrameAnalyzer(QtCore.QObject):
    def __init__(self, device, parent=None):
        super(FrameAnalyzer, self).__init__(parent)
        self.device = device
        self.csv_out = None
        self.tracker = None
        self.animal_start_x = -1
        self.animal_start_y = -1
        self.animal_end_x = -1
        self.animal_end_y = -1

    def init_tracker(self, frame_size):
        self.tracker = Tracker(frame_size)

    def set_background(self, frame, frame_no=0):
        log_msg = "Setting background starting at frame {}.".format(frame_no)
        logger.info(log_msg)
        self.tracker.set_background(frame)

    @staticmethod
    def make_csv_filename(video_filename):
        import os
        import glob
        dirname = os.path.dirname(video_filename)
        basename, _ = os.path.splitext(os.path.basename(video_filename))
        gl = os.path.join(dirname, basename + '_????.csv')
        ex_csv_files = glob.glob(gl)
        if len(ex_csv_files) == 0:
            filename = os.path.join(dirname, basename + '_0001.csv')
        else:
            ex_nos = [int(s[-8:-4]) for s in ex_csv_files]
            csv_no = max(ex_nos) + 1
            csv_no = str(csv_no).zfill(4)
            filename = os.path.join(dirname, basename + '_' + csv_no + '.csv')
        return filename

    def open_csv_files(self):
        filename_csv = self.make_csv_filename(self.device.video_out_filename)
        self.csv_out = open(filename_csv, 'w')

    def close(self):
        if self.csv_out:
            self.csv_out.close()

    def can_track(self):
        return self.tracker is not None

    def start_animal_init(self, x, y):
        self.animal_start_x = x
        self.animal_start_y = y

    def update_animal_init(self, x, y):
        self.animal_end_x = x
        self.animal_end_y = y

    def complete_animal_init(self, x, y, frame_no=0):
        log_msg = "initializing animal at start ({}, {}), end ({}, {}) at frame {}".format(
            self.animal_start_x, self.animal_start_y, x, y, frame_no)
        logger.info(log_msg)
        self.animal_end_x = x
        self.animal_end_y = y
        self.tracker.add_animal(self.animal_start_x, self.animal_start_y,
                                self.animal_end_x, self.animal_end_y)
        self.animal_start_x = -1
        self.animal_start_y = -1

    def process_frame(self, frame):
        if self.tracker:
            self.tracker.track(frame)
            if self.animal_start_x != -1:
                yellow = (255, 255, 0)
                cv2.line(frame, (self.animal_start_x, self.animal_start_y),
                         (self.animal_end_x, self.animal_end_y), yellow, 2)
