import cv2

from PyQt5 import QtCore
from scorer_gui.global_defs import TrialState


class FrameAnalyzer:
    def __init__(self, device):
        self.device = device
        self.csv_out = None

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


class ObjectSpaceFrameAnalyzer(FrameAnalyzer):
    dir_keys = {QtCore.Qt.Key_U: 'UL', QtCore.Qt.Key_7: 'UL',
                QtCore.Qt.Key_O: 'UR', QtCore.Qt.Key_9: 'UR',
                QtCore.Qt.Key_J: 'LL', QtCore.Qt.Key_1: 'LL',
                QtCore.Qt.Key_L: 'LR', QtCore.Qt.Key_3: 'LR',
                QtCore.Qt.Key_T: 'TR'}

    rect_coord = {'UL': (lambda w, h: ((8, 8), (int(w * 0.3), int(h * 0.3)))),
                  'UR': (lambda w, h: ((w - 8, 8), (int(w * 0.7), int(h * 0.3)))),
                  'LL': (lambda w, h: ((8, h - 8), (int(w * 0.3), int(h * 0.7)))),
                  'LR': (lambda w, h: ((w - 8, h - 8), (int(w * 0.7), int(h * 0.7))))}

    def __init__(self, device):
        super(ObjectSpaceFrameAnalyzer, self).__init__(device)
        self.obj_state = {}
        self.device = device
        self.init_obj_state()

    def init_obj_state(self):
        self.obj_state = {'UL': 0, 'UR': 0, 'LR': 0, 'LL': 0, 'TR': 0}

    def process_message(self, msg):
        t = self.device.get_cur_time()
        if msg == 'TR0':
            return
        if msg == 'TR1' and self.device.trial_state != TrialState.COMPLETED:
            trial_on = 1 - self.obj_state['TR']
            self.obj_state['TR'] = trial_on
            print("trial_on: ", trial_on)
            msg = 'TR' + str(trial_on)
            if trial_on:
                self.device.trial_state = TrialState.ONGOING
                if self.device.session:
                    self.device.start_time = self.device.get_absolute_time()
            else:
                self.device.trial_state = TrialState.COMPLETED
        else:
            if self.device.session and  self.device.trial_state != TrialState.ONGOING:
                return
            if msg[:-1] in self.rect_coord and msg[-1] == '1':
                self.obj_state[msg[:-1]] = 1
            else:
                self.obj_state[msg[:-1]] = 0

        if self.device.acquiring and self.device.capturing:
            ts = t.seconds + 1.e-6 * t.microseconds
            if self.device.session:
                self.device.session.set_event(ts, self.device.frame_no, msg)
            elif self.csv_out:
                self.csv_out.write("{},{},{}\n".format(ts, self.device.frame_no, msg))

    def process_frame(self, frame):
        h, w, _ = frame.shape
        for place, state in self.obj_state.items():
            if place in self.rect_coord and state:
                pt1, pt2 = self.rect_coord[place](w, h)
                cv2.rectangle(frame, pt1, pt2, (0, 0, 255), 2)
        if self.obj_state['TR']:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 0), 8)
