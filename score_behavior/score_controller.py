# noinspection PyPackageRequirements
import cv2
import numpy as np
import time
import datetime
import warnings
import logging

from PyQt5 import QtCore

from .global_defs import DeviceState as State

logger = logging.getLogger(__name__)


def find_how_many_cameras():
    print("NOTE: warnings about cameras failing to initialize here below can safely be ignored.")
    for i in range(10):
        # noinspection PyArgumentList
        v = cv2.VideoCapture(i)
        if not v.isOpened():
            return i
        v.release()
    return 1


# the camera model for the Camera acquisition
class DeviceManager(QtCore.QObject):

    new_frame = QtCore.pyqtSignal(np.ndarray, name="CameraDevice.new_frame")
    # can_acquire_signal = QtCore.pyqtSignal(bool, name="CameraDevice.can_acquire_signal")
    # is_acquiring_signal = QtCore.pyqtSignal(bool, name="CameraDevice.is_acquiring_signal")
    # is_paused_signal = QtCore.pyqtSignal(bool, name="CameraDevice.is_paused_signal")
    state_changed_signal = QtCore.pyqtSignal(State, State, name="CameraDevice.state_changed_signal")
    size_changed_signal = QtCore.pyqtSignal(name="CameraDevice.size_changed_signal")
    session_set_signal = QtCore.pyqtSignal(bool, name="CameraDevice.session_set")
    # only to set the label on the window
    video_out_file_changed_signal = QtCore.pyqtSignal(str, name='CameraDevice.video_out_file_changed_signal')
    trial_number_changed_signal = QtCore.pyqtSignal(str, name='CameraDevice.trial_number_changed_signal')
    error_signal = QtCore.pyqtSignal(str, name='CameraDevice.error_signal')
    yes_no_question_signal = QtCore.pyqtSignal(str, name='CameraDevice.yes_no_question_signal')
    yes_no_answer_signal = QtCore.pyqtSignal(bool, name='CameraDevice.yes_no_answer_signal')

    scales_possible = ['0.5', '0.8', '1', '1.5', '2']
    scale_init = 1
    rotate_options = [0, 90, 180, 270]
    rotate_functions = {0: (lambda img: img),
                        90: (lambda img: cv2.flip(cv2.transpose(img), 1)),
                        180: (lambda img: cv2.flip(img, -1)),
                        270: (lambda img: cv2.flip(cv2.transpose(img), 0))}

    def __init__(self, parent=None, session_file=None, analyzer=None):
        super(DeviceManager, self).__init__(parent)

        # initializing image display
        self.mirrored = False
        self.rotate_angle = 0
        self.scale = float(self.scales_possible[self.scale_init])
        self._state = State.NOT_READY

        self._timer = None
        self.interval = 0
        self.session = None
        self.analyzer = analyzer
        if session_file:
            self.set_session(session_file)
        else:
            self._state = State.READY
        self.splash_screen = None
        self.splash_screen_countdown = 0
        self.analyzer = None
        self.dialog = None
        # noinspection PyUnresolvedReferences
        # initialize output
        self.video_out_filename = None
        self.out = None
        self.raw_out = None
        self.display_time = True
        self.save_raw_video = True
        self.yes_no = False
        self.thread = None
        # this flag to close the manager
        self.to_release = False
        self._device = None  # the underlying video source device
        self._device = self.init_device()

        self.start_time = self.get_absolute_time()
        self.frame_no = 0
        self.last_frame = None

        self.capturing = False

        self.track_start_x = -1
        self.track_start_y = -1
        self.track_end_x = 0
        self.track_end_y = 0

    def set_analyzer(self, analyzer):
        self.analyzer = analyzer
        # noinspection PyUnresolvedReferences
        self.state_changed_signal.connect(self.analyzer.device_state_has_changed)

    # Threading support
    def init_thread(self):
        # throw it into a different thread
        self.thread = QtCore.QThread()
        logger.debug("creating thread. id: {}".format(self.thread))
        self.moveToThread(self.thread)
        self.capturing = True
        # noinspection PyUnresolvedReferences
        self.thread.started.connect(self.run)
        self.thread.start()

    @QtCore.pyqtSlot()
    def run(self):
        self._timer = QtCore.QTimer()
        self.interval = int(1.e3 / self.fps)
        logger.debug("starting timer with interval {}".format(self.interval))
        self._timer.setInterval(self.interval)
        # noinspection PyUnresolvedReferences
        self._timer.timeout.connect(self.query_frame)
        self._timer.start()
        self.size_changed_signal.emit()

    def init_device(self):
        return None  # "pure virtual" function

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def set_session(self, filename):
        return None  # pure virtual

    @QtCore.pyqtSlot(int)
    def change_scale(self, i):
        self.scale = float(self.scales_possible[i])
        logger.debug("Scale changed to {}".format(self.scale))
        self.size_changed_signal.emit()

    # @property
    # def can_acquire(self):
    #     # this means that we have a input and output devices ready
    #     return self._can_acquire
    #
    # @can_acquire.setter
    # def can_acquire(self, val):
    #     self._can_acquire = val
    #     self.can_acquire_signal.emit(val)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        prev_state = self._state
        self._state = val
        if val == State.ACQUIRING:
            self.start_time = self.get_absolute_time()
            self.frame_no = 0
        self.state_changed_signal.emit(val, prev_state)
        logger.debug("State changed to {}".format(self.state))

    @QtCore.pyqtSlot()
    def start_trial_acquisition(self):
        if self.state == State.NOT_READY:
            return
        logger.debug('starting trial acquisition')
        self.state = State.ACQUIRING

    @QtCore.pyqtSlot()
    def stop_trial_acquisition(self):
        logging.debug("Ending trial acquisition")
        self.state = State.READY

    @QtCore.pyqtSlot()
    def stop_acquisition(self):
        logging.debug("Stopping acquisition")
        self.state = State.FINISHED

    @QtCore.pyqtSlot(bool)
    def set_mirror(self, mirrored):
        logging.debug("setting mirrored to {}".format(mirrored))
        self.mirrored = mirrored

    @QtCore.pyqtSlot(int)
    def set_rotate(self, i):
        self.rotate_angle = self.rotate_options[i]
        logger.debug("Setting rotate to {}".format(self.rotate_angle))
        self.size_changed_signal.emit()

    @QtCore.pyqtSlot(bool)
    def set_raw_out(self, val):
        self.save_raw_video = val

    @QtCore.pyqtSlot(bool)
    def set_display_time(self, val):
        self.display_time = val

    @QtCore.pyqtSlot(str)
    def set_out_video_file(self, filename):
        self.video_out_filename = filename
        self.open_video_out_files()

    @QtCore.pyqtSlot(bool)
    def yes_no_answer(self, i):
        self.yes_no_answer_signal.emit(i)
        self.yes_no = i

    def open_video_out_files(self, filename=None):
        import os
        logger.info("Attempting to open video file {} for writing ".format(self.video_out_filename))
        if os.path.exists(filename):
            logger.error("File {} exists, ".format(self.video_out_filename))
            self.error_signal.emit("File {} exists, this shouldn't happen. Cannot continue".
                                   format(self.video_out_filename))
        import platform
        codec_string = ''
        if platform.system() == 'Darwin':
            codec_string = 'mp4v'
        elif platform.system() == 'Linux':
            codec_string = 'MJPG'
        elif platform.system() == 'Windows':
            codec_string = 'MSVC'

        fourcc = cv2.VideoWriter_fourcc(*codec_string)
        if self.out:
            self.out.release()
            self.out = None
        self.out = cv2.VideoWriter(filename, fourcc, self.fps, self.frame_size)
        if self.save_raw_video:
            if self.raw_out:
                self.raw_out.release()
                self.raw_out = None
            self.raw_out = cv2.VideoWriter(self.make_raw_filename(filename), fourcc, self.fps, self.frame_size)
        if self.out.isOpened():
            self.state = State.READY
            logger.info("successfully opened video out file {}".format(filename))
        else:
            import warnings
            self.state = State.NOT_READY
            warnings.warn("Can't open output file!!")
            logger.error("Can't open output file {}".format(filename))
            self.error_signal.emit("Can't open output file {}".format(filename))

        self.video_out_file_changed_signal.emit("Video: " + os.path.basename(filename))

    def close_video_out_files(self):
        if self.out:
            self.out.release()
            self.out = None
        if self.raw_out:
            self.raw_out.release()
            self.raw_out = None
        logger.debug("closed video files for trial")

    @staticmethod
    def make_raw_filename(video_filename):
        import os
        dirname = os.path.dirname(video_filename)
        basename, _ = os.path.splitext(os.path.basename(video_filename))
        filename = os.path.join(dirname, basename + '_raw.avi')
        return filename

    @QtCore.pyqtSlot()
    def query_frame(self):
        pass  # pure virtual function

    def add_timestamp_string(self, frame):
        if self.state == State.ACQUIRING and self.display_time:
            h, w, _ = frame.shape
            cur_time = str(self.get_cur_time())[:-4]
            font = cv2.FONT_HERSHEY_DUPLEX
            # noinspection PyUnusedLocal
            t_size, baseline = cv2.getTextSize(cur_time, font, 0.5, 1)
            tpt = 5, h - 5
            cv2.putText(frame, cur_time, tpt, font, 0.5, (0, 0, 255), 1)
            cur_frame = str(self.frame_no)
            t_size, baseline = cv2.getTextSize(cur_time, font, 0.5, 1)
            tpt = 5, h - 5 - t_size[1]
            cv2.putText(frame, cur_frame, tpt, font, 0.5, (0, 255, 255), 1)

    def get_cur_time(self):
        """get current time, null implementation"""
        return datetime.timedelta(0)

    def get_absolute_time(self):
        """return current absolute time, null implementation"""
        return None

    @QtCore.pyqtSlot()
    def cleanup(self):

        self.state = State.NOT_READY
        self.to_release = True
        if self.thread:
            self.thread.wait()
            logger.debug("Acquisition thread exited")

    def release(self):
        logger.info("releasing acquisition device and stopping")
        time.sleep(0.5)
        # if self._device:
        #     self._device.release()
        if self.out:
            self.out.release()
            self.out = None
        if self.thread:
            self.thread.quit()

    @property
    def display_frame_size(self):
        return None, None  # pure virtual

    @property
    def frame_size(self):
        return None, None  # pure virtual

    @property
    def fps(self):
        return 0  # pure virtual

    def process_frame(self, frame):
        if self.analyzer:
            self.analyzer.process_frame(frame)
        self.add_timestamp_string(frame)


class VideoDeviceManager(DeviceManager):
    video_finished_signal = QtCore.pyqtSignal(name="CameraDevice.video_finished_signal")
    frame_pos_signal = QtCore.pyqtSignal(int, name="CameraDevice.frame_pos_signal")
    time_pos_signal = QtCore.pyqtSignal(str, name="CameraDevice.time_pos_signal")

    speed_possible = ['0.5', '0.8', '1', '1.2', '1.5', '2']

    def __init__(self, video_file=None, parent=None, session_file=None, widget=None, analyzer=None):
        self.video_file = video_file
        super(VideoDeviceManager, self).__init__(parent=parent, session_file=session_file, analyzer=analyzer)
        self.save_raw_video = False
        self.playback_speed = 1.
        self.init_thread()
        self.is_paused = False
        self.widget = widget

    def init_device(self):
        # noinspection PyArgumentList
        cd = cv2.VideoCapture(self.video_file)
        if not cd.isOpened():
            logger.error("Could not open video file {}".format(self.video_file))
            raise RuntimeError("Could not open video file {}".format(self.video_file))
        return cd

    def video_last_frame(self):
        return self._device.get(cv2.CAP_PROP_FRAME_COUNT)

    @staticmethod
    def timedelta_to_string(td):
        import math
        ts = td.total_seconds()
        td1 = datetime.timedelta(seconds=math.floor(ts * 100) / 100)
        tds = str(td1)
        if '.' not in tds:
            tds = tds + '.00'
        else:
            tds = tds[:-4]
        return tds

    @QtCore.pyqtSlot()
    def query_frame(self):
        #     import cProfile  #  this is for profiling only
        #     cProfile.runctx("self.query_frame_()", globals(), locals(), filename='profile.stat')
        #
        # def query_frame_(self):
        # print("starts querying")
        # print("paused: {}, capturing: {}, acquiring: {}".format(self.paused, self.capturing, self.acquiring))

        if self.state == State.NOT_READY or self.is_paused is True:
            return

        ret, frame = self._device.read()

        if ret:
            self.frame_no = int(self._device.get(cv2.CAP_PROP_POS_FRAMES))
            self.last_frame = frame
            self.frame_pos_signal.emit(self.frame_no)

            tds = self.timedelta_to_string(self.get_cur_time())

            self.time_pos_signal.emit(tds)

            h, w, _ = frame.shape

            if self.state == State.ACQUIRING:
                if self.save_raw_video and self.raw_out:
                    self.raw_out.write(frame)
                self.process_frame(frame)  # should it be called only when recording?

                if self.out:
                    self.out.write(frame)

            self.new_frame.emit(frame)
        else:
            self.video_finished_signal.emit()
            self.state = State.NOT_READY

        if self.to_release:
            self.release()

    @property
    def display_frame_size(self):
        w = int(self._device.get(cv2.CAP_PROP_FRAME_WIDTH) * self.scale)
        h = int(self._device.get(cv2.CAP_PROP_FRAME_HEIGHT) * self.scale)
        return int(w), int(h)

    @property
    def frame_size(self):
        w = int(self._device.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._device.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return int(w), int(h)

    @QtCore.pyqtSlot(int)
    def skip_to_frame(self, val):
        self._device.set(cv2.CAP_PROP_POS_FRAMES, float(val))
        self.frame_no = val

    @property
    def fps(self):
        fps = int(self._device.get(cv2.CAP_PROP_FPS))
        return fps

    def get_cur_time(self):
        # return datetime.timedelta(milliseconds=self._device.get(cv2.CAP_PROP_POS_MSEC))
        return datetime.timedelta(milliseconds=1000 * self.frame_no / self.fps)

    def set_session(self, filename):
        if self.analyzer:
            ret = self.analyzer.set_session(filename, mode='video')
            if ret == 0:
                self.state = State.READY

    def move_to_frame(self, frame_no):
        if frame_no < self.frame_no:
            warnings.warn("can't skip to earlier frame")
        while self._device.get(cv2.CAP_PROP_POS_FRAMES) < frame_no:
            self._device.read()
        self.frame_no = frame_no

    def set_speed(self, speed):
        self.playback_speed = speed
        self.interval = int(1.e3 / (self.fps * speed))
        self._timer.setInterval(self.interval)

    @QtCore.pyqtSlot()
    def rewind_action(self):
        new_frame = self.frame_no - 60 * self.fps
        self.skip_to_frame(new_frame)

    @QtCore.pyqtSlot()
    def fastforward_action(self):
        new_frame = self.frame_no + 60 * self.fps
        self.skip_to_frame(new_frame)

    @QtCore.pyqtSlot()
    def play_action(self):
        self.is_paused = False
        self.widget.ui.playButton.setEnabled(False)
        self.widget.ui.pauseButton.setEnabled(True)

    @QtCore.pyqtSlot()
    def pause_action(self):
        self.is_paused = True
        self.widget.ui.playButton.setEnabled(True)
        self.widget.ui.pauseButton.setEnabled(False)

    @QtCore.pyqtSlot(int)
    def speed_action(self, i):
        speed = float(self.speed_possible[i])
        self.set_speed(speed)
        logger.debug("changed speed to {}".format(speed))


class CameraDeviceManager(DeviceManager):
    _DEFAULT_FPS = 30

    def __init__(self, camera_id=0, parent=None, session_file=None, analyzer=None):
        self.camera_id = camera_id
        super(CameraDeviceManager, self).__init__(parent=parent, session_file=session_file, analyzer=analyzer)
        self.init_thread()
        self.state = State.READY

    def init_device(self):
        # print(cv2.getBuildInformation())
        # noinspection PyArgumentList
        cd = cv2.VideoCapture(0)
        # cd = cv2.VideoCapture(self.camera_id)
        if not cd.isOpened():
            logger.error("Could not initialize camera id {}".format(self.camera_id))
            raise RuntimeError("Could not initialize camera id {}".format(self.camera_id))
        return cd

    @QtCore.pyqtSlot()
    def query_frame(self):
        if self.to_release:
            self.release()
        if self.state in (State.READY, State.ACQUIRING):
            if self.splash_screen_countdown:
                frame = self.analyzer.splash_screen
                ret = True
                if self.splash_screen_countdown == 1:
                    self.analyzer.trial_state = self.analyzer.TrialState.READY
                else:
                    pass
                    # self.trial_state = TrialState.COMPLETED
                self.splash_screen_countdown -= 1
            else:
                ret, frame = self._device.read()
                if ret:
                    h, w, _ = frame.shape
                    frame = self.rotate_functions[self.rotate_angle](frame)
                    if self.mirrored:
                        frame = cv2.flip(frame, 1)
            if ret:
                self.frame_no += 1
                if self.state == State.ACQUIRING:
                    if self.save_raw_video and self.raw_out:
                        self.raw_out.write(frame)
                    if self.splash_screen_countdown == 0:
                        self.process_frame(frame)

                    if self.out:
                        self.out.write(frame)
                h, w, _ = frame.shape
                frame_display = cv2.resize(frame, (int(w * self.scale), int(h * self.scale)),
                                           interpolation=cv2.INTER_AREA)

                self.new_frame.emit(frame_display)
            else:
                logger.info("Camera lost")
                raise RuntimeError("Camera Lost")
            # else:
                #  notify that camera is not acquiring ?
                # self.video_finished_signal.emit()
                # self.paused = True

    @property
    def display_frame_size(self):
        w = int(self._device.get(cv2.CAP_PROP_FRAME_WIDTH) * self.scale)
        h = int(self._device.get(cv2.CAP_PROP_FRAME_HEIGHT) * self.scale)
        if self.rotate_angle in (90, 270):
            w, h = h, w
        return int(w), int(h)

    @property
    def frame_size(self):
        w = int(self._device.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._device.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if self.rotate_angle in (90, 270):
            w, h = h, w
        return int(w), int(h)

    @property
    def fps(self):
        fps = self._DEFAULT_FPS
        return fps

    def get_cur_time(self):
        if self.session:
            if self.trial_state != self.TrialState.ONGOING:
                return datetime.timedelta(0)
            else:
                return datetime.datetime.now() - self.start_time
        else:
            return datetime.datetime.now() - self.start_time

    def get_absolute_time(self):
        return datetime.datetime.now()

    def set_session(self, filename):
        if self.analyzer:
            self.analyzer.set_session(filename, mode='live')
