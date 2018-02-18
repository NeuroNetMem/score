import cv2

from PyQt5 import QtCore

from score_behavior.score_analyzer import FrameAnalyzer
from score_behavior.global_defs import DeviceState
import logging

from .dialog_controller import TrialDialogController
logger = logging.getLogger(__name__)


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
    dialog_trigger_signal = QtCore.pyqtSignal(name="ObjectSpaceFrameAnalyzer.dialog_trigger_signal")

    def __init__(self, device, parent=None):
        super(ObjectSpaceFrameAnalyzer, self).__init__(device, parent=parent)
        self.obj_state = {}
        self.device = device
        self.init_obj_state()
        self.track_start_x = -1
        self.track_start_y = -1
        self.track_end_x = -1
        self.track_end_y = -1
        self.dialog = None
        self.r_keys = list(self.rect_coord.keys())

    def set_session(self, filename, mode='live'):
        super(ObjectSpaceFrameAnalyzer, self).set_session(filename, mode)
        self.dialog = TrialDialogController(self, list(self.rect_coord.keys()), object_dir=self.session.object_dir,
                                            object_list=self.session.get_object_list())
        # noinspection PyUnresolvedReferences
        self.dialog_trigger_signal.connect(self.dialog.start_dialog)

    def start_trial_dialog(self):
        self.dialog_trigger_signal.emit()

    def init_obj_state(self):
        self.obj_state = {'UL': 0, 'UR': 0, 'LR': 0, 'LL': 0, 'TR': 0}

    def process_message(self, msg):
        logger.debug("Analyzer got message {}".format(msg))
        t = self.device.get_cur_time()
        if msg == 'TR0':
            return
        if msg == 'TR1' and self.trial_state != self.TrialState.COMPLETED:
            trial_on = 1 - self.obj_state['TR']
            self.obj_state['TR'] = trial_on
            msg = 'TR' + str(trial_on)
            if trial_on:
                self.trial_state = self.TrialState.ONGOING
                self.device.start_time = self.device.get_absolute_time()
            else:
                self.trial_state = self.TrialState.COMPLETED
        else:
            if self.trial_state != self.TrialState.ONGOING:
                return
            if msg[:-1] in self.rect_coord and msg[-1] == '1':
                self.obj_state[msg[:-1]] = 1
            else:
                self.obj_state[msg[:-1]] = 0

        if self.device.state == DeviceState.ACQUIRING:
            ts = t.seconds + 1.e-6 * t.microseconds
            self.session.set_event(ts, self.device.frame_no, msg)

    def process_frame(self, frame):
        h, w, _ = frame.shape
        super(ObjectSpaceFrameAnalyzer, self).process_frame(frame)
        for place, state in self.obj_state.items():
            if place in self.rect_coord and state:
                pt1, pt2 = self.rect_coord[place](w, h)
                cv2.rectangle(frame, pt1, pt2, (0, 0, 255), 2)
        if self.obj_state['TR']:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 0), 8)

    @QtCore.pyqtSlot(int, int)
    def mouse_press_action(self, x, y):
        self.track_start_x = x
        self.track_start_y = y
        self.start_animal_init(x, y)

    @QtCore.pyqtSlot(int, int)
    def mouse_move_action(self, x, y):
        if x == -1:
            self.track_start_x = -1
            self.track_start_y = -1
            self.start_animal_init(-1, -1)
        else:
            self.track_end_x = x
            self.track_end_y = y
            self.update_animal_init(x, y)

    @QtCore.pyqtSlot(int, int)
    def mouse_release_action(self, x, y):
        if self.track_start_x == -1:
            return
        if x == -1:
            self.track_start_x = -1
            self.track_start_y = -1
            self.start_animal_init(-1, -1)
        else:
            self.track_end_x = x
            self.track_end_y = y
            self.complete_animal_init(x, y, frame_no=self.device.frame_no)
