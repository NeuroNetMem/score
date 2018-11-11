import cv2

from PyQt5 import QtCore
from score_behavior.score_analyzer import FrameAnalyzer
from score_behavior.global_defs import DeviceState
import logging

from .dialog_controller import TrialDialogController
logger = logging.getLogger(__name__)


# noinspection PyAttributeOutsideInit
class ObjectSpaceFrameAnalyzer(FrameAnalyzer):
    dir_keys = {QtCore.Qt.Key_U: 'UL', QtCore.Qt.Key_7: 'UL',
                QtCore.Qt.Key_O: 'UR', QtCore.Qt.Key_9: 'UR',
                QtCore.Qt.Key_J: 'LL', QtCore.Qt.Key_1: 'LL',
                QtCore.Qt.Key_L: 'LR', QtCore.Qt.Key_3: 'LR',
                QtCore.Qt.Key_T: 'TR'}

    dialog_trigger_signal = QtCore.pyqtSignal(name="ObjectSpaceFrameAnalyzer.dialog_trigger_signal")
    post_trial_dialog_trigger_signal = \
        QtCore.pyqtSignal(str, str, name="ObjectSpaceFrameAnalyzer.post_trial_dialog_trigger_signal")

    def __init__(self, device, parent=None):
        super(ObjectSpaceFrameAnalyzer, self).__init__(device, parent=parent)
        self.obj_state = {}
        self.rect_coord = {'UL': lambda w, h: (None, None),
                           'UR': lambda w, h: (None, None),
                           'LL': lambda w, h: (None, None),
                           'LR': lambda w, h: (None, None)}
        self.device = device

        self.init_obj_state()

        self.dialog = None
        self.r_keys = list(self.rect_coord.keys())

    def set_session(self, filename, mode='live', first_trial=0):
        ret = super(ObjectSpaceFrameAnalyzer, self).set_session(filename, mode, first_trial=first_trial)
        self.dialog = TrialDialogController(self, list(self.rect_coord.keys()),
                                            object_files=self.session.get_object_files())
        # noinspection PyUnresolvedReferences
        self.dialog_trigger_signal.connect(self.dialog.start_dialog)
        return ret

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, dev):
        self._device = dev
        if dev:
            self.device.state_changed_signal.connect(self.session_controller.change_state)
            th = self.device.top_info_band_height-2
            bh = self.device.bottom_info_band_height-2
            self.rect_coord = {'UL': (lambda w, h: ((0, 0), (th, th))),
                               'UR': (lambda w, h: ((w - th, 0), (w, th))),
                               'LL': (lambda w, h: ((0, h - bh), (bh, h))),
                               'LR': (lambda w, h: ((w - bh, h - bh), (w, h)))}

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
                cv2.rectangle(frame, pt1, pt2, (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        tpt = 300, self.device.top_info_band_height-2
        if self.obj_state['TR']:
            cv2.putText(frame, "Trial: on", tpt, font, 0.5, (255, 255, 255), 1)
        else:
            cv2.putText(frame, "Trial: off", tpt, font, 0.5, (255, 255, 255), 1)

    def finalize_trial(self):
        scheme = self.session.get_scheme_trial_info()
        if "posttrial_instructions" in scheme and isinstance(scheme["posttrial_instructions"], str):
            text = scheme['posttrial_instructions']
            text = text.replace("|", "<br/>")
            text = "Post Trial Instructions:<br/>" + text
            self.post_trial_dialog_trigger_signal.emit("Post Trial Instructions", text)
        super(ObjectSpaceFrameAnalyzer, self).finalize_trial()
