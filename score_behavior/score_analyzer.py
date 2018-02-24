from enum import Enum
import cv2
from PyQt5 import QtCore
from PyQt5 import QtWidgets
import numpy as np

import logging
import datetime
from score_behavior.tracking.tracker import Tracker
from score_behavior.ObjectSpace.session_manager import ObjectSpaceSessionManager
from score_behavior.score_session_controller import SessionController
from score_behavior.global_defs import DeviceState as State
from score_behavior.tracking_controller.tracker_controller import TrackerController
from score_behavior.score_config import get_config_section

logger = logging.getLogger(__name__)


class FrameAnalyzer(QtCore.QObject):
    class TrialState(Enum):
        IDLE = 1
        READY = 2
        ONGOING = 3
        COMPLETED = 4

    trial_state_changed_signal = QtCore.pyqtSignal(TrialState, name="FrameAnalyzer.trial_state_changed_signal")
    trial_number_changed_signal = QtCore.pyqtSignal(str, name="FrameAnalyzer.trial_state_changed_signal")
    error_signal = QtCore.pyqtSignal(str, name="FrameAnalyzer.error_signal")
    session_set_signal = QtCore.pyqtSignal(bool, name="FrameAnalyzer.session_set_signal")

    def __init__(self, device, parent=None):
        super(FrameAnalyzer, self).__init__(parent)
        self.do_track = False
        self.trial_duration_seconds = 0
        self.read_config()
        self.device = device
        self.csv_out = None
        self.tracker = None
        self.tracker_controller = None
        self.session_controller = None

        self._trial_state = self.TrialState.IDLE

        self.animal_start_x = -1
        self.animal_start_y = -1
        self.animal_end_x = -1
        self.animal_end_y = -1
        self.session = None
        self.splash_screen = None
        self.mode = None
        self.video_out_filename = None
        self.r_keys = []
        self.dialog = None
        self.video_out_raw_filename = None
        self.track_start_x = -1
        self.track_start_y = -1
        self.track_end_x = -1
        self.track_end_y = -1

    def read_config(self):
        d = get_config_section("analyzer")
        if "do_track" in d:
            self.do_track = bool(d["do_track"])
        if "trial_duration_seconds" in d:
            self.trial_duration_seconds = datetime.timedelta(seconds=d['trial_duration_seconds'])

    @property
    def trial_state(self):
        return self._trial_state

    @trial_state.setter
    def trial_state(self, val):
        self._trial_state = val
        logger.debug("Trial state changed to {}".format(self.trial_state))
        self.trial_state_changed_signal.emit(self._trial_state)

    @QtCore.pyqtSlot(State, State)
    def device_state_has_changed(self, val, prev_val):
        if val == State.ACQUIRING:
            self.trial_setup()
        elif val == State.READY:
            if prev_val == State.ACQUIRING:
                self.finalize_trial()
        elif val == State.FINISHED:
            self.session.close()
            self.session = None

    @QtCore.pyqtSlot(str)
    def obj_state_change(self, msg):
        logger.debug("Got message {}".format(msg))
        if self.trial_state in (self.TrialState.IDLE, self.TrialState.COMPLETED):
            return
        self.process_message(msg)

    def key_interface(self):
        return self.dir_keys

    def set_session(self, filename, mode='live'):
        self.mode = mode
        try:
            # noinspection PyUnresolvedReferences,PyCallByClass,PyTypeChecker
            init_trial, ok = QtWidgets.QInputDialog.getInt(None,
                                                           "Initial trial",
                                                           "Please enter the first scheme trial for this session",
                                                           1, min=1, flags=QtCore.Qt.WindowFlags())
            if not ok:
                init_trial = 1
            logger.debug("Attempting to start {} session from file {} and from trial {}".format(self.mode, filename,
                                                                                                init_trial))
            try:
                self.session = ObjectSpaceSessionManager(filename, initial_trial=init_trial, min_free_disk_space=25,
                                                         mode=mode, r_keys=self.r_keys)
                self.session_controller = SessionController(parent=self.parent(), data=self.session.scheme)
                self.parent().ui.sidebarWidget.layout().addWidget(self.session_controller.widget)
                self.session_controller.widget.setFocusPolicy(QtCore.Qt.NoFocus)
                self.session_controller.comments_inserted_signal.connect(self.set_comments)
                self.session_controller.skip_trial_signal.connect(self.skip_trial)
                self.device.state_changed_signal.connect(self.session_controller.change_state)

                self.parent().setFocus()
            except Exception as e:
                import traceback
                logger.error("Could not start session from file {}  Error {}".format(filename, traceback.format_exc()))
                self.error_signal.emit(str(e))
                return -1

            self.session_set_signal.emit(True)
            logger.debug("Session correctly opened")
            return 0

        except ValueError as e:
            logger.error("Could not start session from file {}. ValueError {}".format(filename, str(e)))
            self.session = None
            self.session_set_signal.emit(False)
            import warnings
            warnings.warn(str(e))
            return -1

    def start_trial_dialog(self):
        pass

    def trial_setup(self):
        scheme = self.session.get_scheme_trial_info()

        logger.debug("starting setting up trial")
        self.dialog.set_scheme(scheme)
        self.start_trial_dialog()

        if self.dialog.exit_status():
            self.session.set_trial_results_info(self.dialog.get_values())
        else:
            self.device.state = State.READY
            return
        logger.info("back to trial_setup")
        self.device.setup_input_for_trial()
        self.video_out_filename, self.video_out_raw_filename = self.session.get_video_out_file_name_for_trial()
        self.device.open_video_out_files(self.video_out_filename, self.video_out_raw_filename)
        self.session.set_comments('')
        trial_info = self.session.get_trial_results_info()
        self.make_splash_screen(trial_info)
        self.trial_number_changed_signal.emit(str(trial_info['sequence_nr']))
        logger.debug("Finished setting up Trial {}".format(trial_info['sequence_nr']))
        if self.session_controller:
            self.session_controller.set_current_row(trial_info['run_nr'])
        self.trial_state = self.TrialState.READY

    def add_trial(self):
        if self.session:
            logger.debug("Adding trial")
            self.session.add_trial()
            self.dialog.set_scheme(self.session.get_scheme_trial_info(), new_trial=True)
            self.dialog.set_readonly(False)

    def skip_trial(self):
        if self.session:
            logger.debug("Skipping trial")
            self.session.skip_trial()
            if self.dialog:
                self.dialog.set_scheme(self.session.get_scheme_trial_info())
            if self.session_controller:
                csr = self.session.cur_scheduled_run
                self.session_controller.set_current_row(csr)

    def finalize_trial(self):
        if self.trial_state not in (self.TrialState.IDLE, self.TrialState.READY):
            logger.debug("Finalizing trial")
            if self.trial_state == self.TrialState.ONGOING:
                t = self.device.get_cur_time()
                ts = t.seconds + 1.e-6 * t.microseconds
                self.session.set_event(ts, self.device.frame_no, 'TR0')
                self.process_message('TR1')
                self.trial_state = self.TrialState.COMPLETED
            self.device.close_video_out_files()
            self.session.analyze_trial()
            self.session.set_trial_finished(self.video_out_filename, self.video_out_raw_filename)
        self.trial_state = self.TrialState.IDLE
        if self.tracker:
            self.tracker.delete_all_animals()

    def make_splash_screen(self, trial_info):
        width, height = self.device.frame_size
        self.device.splash_screen_countdown = self.device.fps * 3  # show the splash screen for three seconds
        self.splash_screen = np.zeros((height, width, 3), np.uint8)

        font = cv2.FONT_HERSHEY_DUPLEX
        str1 = "Session " + str(trial_info['session']) + "  Trial " + str(trial_info['sequence_nr']) + " Schedule " + \
            str(trial_info['run_nr'])
        t_size, baseline = cv2.getTextSize(str1, font, 1, 1)
        tpt = (width-t_size[0])//2, 15
        cv2.putText(self.splash_screen, str1, tpt, font, 0.5, (0, 255, 255), 1)

        str1 = trial_info['start_date']
        t_size, baseline = cv2.getTextSize(str1, font, 1, 1)
        tpt = (width - t_size[0]) // 2, tpt[1] + int((t_size[1]+baseline)*1.5)
        cv2.putText(self.splash_screen, str1, tpt, font, 0.5, (0, 255, 255), 1)

        str1 = "Subject " + str(trial_info['subject'])
        t_size, baseline = cv2.getTextSize(str1, font, 1, 1)
        tpt = (width - t_size[0]) // 2, tpt[1] + int((t_size[1]+baseline)*1.5)
        cv2.putText(self.splash_screen, str1, tpt, font, 0.5, (0, 255, 255), 1)

        return self.splash_screen

    def acquire_background(self, frame_no=None):
        if frame_no is not None:
            self.move_to_frame(frame_no)
        ret, frame = self._device.read()
        if ret:
            self.set_background(frame, self.frame_no)
        else:
            raise RuntimeError("Can't read frame!")

    def add_animal(self, start, end, frame_no=None):
        if frame_no is not None:
            self.move_to_frame(frame_no)
        self.start_animal_init(start[0], start[1])
        self.complete_animal_init(end[0], end[1], self.frame_no)

    def init_tracker(self, frame_size):
        if not self.do_track:
            return
        if self.tracker is None:
            self.tracker = Tracker(frame_size)
        if self.tracker_controller is None:
            self.tracker_controller = TrackerController(self.tracker, parent=None)
            self.parent().ui.sidebarWidget.layout().addWidget(self.tracker_controller.widget)
        # if self._analyzer.tracker:
        #     self.ui.sidebarWidget.layout().addWidget(self._analyzer.tracker_controller.widget)

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
        self.tracker.add_animal(int(self.animal_start_x / self.device.scale),
                                int(self.animal_start_y / self.device.scale),
                                int(self.animal_end_x / self.device.scale), int(self.animal_end_y / self.device.scale))
        self.animal_start_x = -1
        self.animal_start_y = -1

    @QtCore.pyqtSlot(str)
    def set_comments(self, comments):
        if self.session:
            self.session.set_comments(comments)

    def process_frame(self, frame):
        if self.tracker:
            position_data = self.tracker.track(frame)
            if position_data:
                for px in position_data:
                    px['cur_time'] = self.device.get_cur_time()
                    px['frame'] = self.device.frame_no
                self.session.set_position_data(position_data)

            if self.animal_start_x != -1:
                yellow = (0, 255, 255)
                cv2.line(frame, (int(self.animal_start_x / self.device.scale),
                                 int(self.animal_start_y / self.device.scale)),
                                (int(self.animal_end_x / self.device.scale),
                                 int(self.animal_end_y / self.device.scale)), yellow, 2)

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
