# noinspection PyPackageRequirements
import cv2
import numpy as np
import time
import datetime

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from scorer_gui.session_manager import VideoSessionManager, LiveSessionManager


def find_how_many_cameras():
    print("NOTE: warnings about cameras failing to initialize here below can safely be ignored.")
    for i in range(10):
        # noinspection PyArgumentList
        v = cv2.VideoCapture(i)
        if not v.isOpened():
            return i
        v.release()


class OpenCVQImage(QtGui.QImage):
    def __init__(self, opencv_bgr_img):

        h, w, n_channels = opencv_bgr_img.shape
        depth = opencv_bgr_img.dtype
        if depth != np.uint8 or n_channels != 3:
            raise ValueError("the input image must be 8-bit, 3-channel")

        # it's assumed the image is in BGR format
        opencv_rgb_img = cv2.cvtColor(opencv_bgr_img, cv2.COLOR_BGR2RGB)
        self._imgData = opencv_rgb_img.tostring()
        super(OpenCVQImage, self).__init__(self._imgData, w, h,
                                           QtGui.QImage.Format_RGB888)


class TrialDialogController(QtCore.QObject):
    dialog_done_signal = QtCore.pyqtSignal(name="TrialDialogController.dialog_done_signal")

    def __init__(self, caller, locations, parent=None):
        super(TrialDialogController, self).__init__(parent)
        self.caller = caller
        self.scheme = None
        self.locations = locations
        self.dialog = None
        self.ok = False

    def set_scheme(self, scheme):
        self.scheme = scheme
        if self.dialog:
            self.dialog.set_values(scheme)

    def get_values(self):
        return self.dialog.get_values()

    @QtCore.pyqtSlot()
    def start_dialog(self):
        from scorer_gui.obj_scorer import TrialDialog
        self.dialog = TrialDialog(caller=self.caller, trial_params=self.scheme, locations=self.locations)
        self.dialog.set_readonly(True)
        self.ok = self.dialog.exec_()
        self.dialog_done_signal.emit()

    def exit_status(self):
        return self.ok

    def set_readonly(self, i):
        self.dialog.set_readonly(i)


# the camera model for the Camera acquisition
class DeviceManager(QtCore.QObject):
    new_frame = QtCore.pyqtSignal(np.ndarray, name="CameraDevice.new_frame")
    can_acquire_signal = QtCore.pyqtSignal(bool, name="CameraDevice.can_acquire_signal")
    is_acquiring_signal = QtCore.pyqtSignal(bool, name="CameraDevice.is_acquiring_signal")
    is_paused_signal = QtCore.pyqtSignal(bool, name="CameraDevice.is_paused_signal")
    size_changed_signal = QtCore.pyqtSignal(name="CameraDevice.size_changed_signal")
    session_set_signal = QtCore.pyqtSignal(bool, name="CameraDevice.session_set")
    dialog_trigger_signal = QtCore.pyqtSignal(name="CameraDevice.dialog_trigger_signal")

    scales_possible = ['0.5', '0.8', '1', '1.5', '2']
    scale_init = 1
    rotate_options = [0, 90, 180, 270]
    rotate_functions = {0: (lambda img: img),
                        90: (lambda img: cv2.flip(cv2.transpose(img), 1)),
                        180: (lambda img: cv2.flip(img, -1)),
                        270: (lambda img: cv2.flip(cv2.transpose(img), 0))}

    def __init__(self, parent=None, session_file=None):
        super(DeviceManager, self).__init__(parent)

        # initialize tracking controller
        self.obj_state = {}
        self.init_obj_state()

        # initializing image display
        self.mirrored = False
        self.rotate_angle = 0
        self.scale = float(self.scales_possible[self.scale_init])
        self._can_acquire = False
        self._acquiring = False
        self._paused = False
        self._timer = None
        self.session = None
        if session_file:
            self.set_session(session_file)
        self.splash_screen = None
        self.splash_screen_countdown = 0
        self.dialog = TrialDialogController(self, list(self.rect_coord.keys()))
        # noinspection PyUnresolvedReferences
        self.dialog_trigger_signal.connect(self.dialog.start_dialog)
        # initialize output
        self.video_out_filename = None
        self.out = None
        self.raw_out = None
        self.csv_out = None
        self.display_time = True
        self.save_raw_video = True

        self.thread = None
        # this flag to close the manager
        self.to_release = False

        self._device = None
        # self._device = self.init_device()
        # prepare timer
        self.interval = int(1.e3 / self.fps)
        self.start_time = datetime.datetime.now()
        self.frame_no = 0

        self.trial_ongoing = False
        self.trial_ready = False
        self.capturing = False
        # noinspection PyArgumentList
        # print("init_thread: ", int(QtCore.QThread.currentThreadId()))

    def init_thread(self):
        # throw it into a different thread
        self.thread = QtCore.QThread()
        # print("creating thread: ", self.thread, " id: ")
        self.moveToThread(self.thread)
        self.capturing = True
        # noinspection PyUnresolvedReferences
        self.thread.started.connect(self.run)
        self.thread.start()

    @QtCore.pyqtSlot()
    def run(self):
        # noinspection PyArgumentList
        # print("running in thread: ", QtCore.QThread.currentThread(), " id: ", int(QtCore.QThread.currentThreadId()))
        # noinspection PyCallByClass
        self._timer = QtCore.QTimer()
        self._timer.setInterval(self.interval)
        # noinspection PyUnresolvedReferences
        self._timer.timeout.connect(self.query_frame)
        self._device = self.init_device()
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
        self.size_changed_signal.emit()

    @property
    def can_acquire(self):
        # this means that we have a input and output devices ready
        return self._can_acquire

    @can_acquire.setter
    def can_acquire(self, val):
        self._can_acquire = val
        self.can_acquire_signal.emit(val)

    @property
    def acquiring(self):
        # this means that we are acquiring
        #  TODO verify if it can be merged with paused
        return self._acquiring

    @acquiring.setter
    def acquiring(self, val):
        if val:
            self.start_time = datetime.datetime.now()
            self.frame_no = 0
        self._acquiring = val
        self.is_acquiring_signal.emit(val)

    def trial_setup(self):
        scheme = self.session.get_scheme_trial_info()
        self.dialog.set_scheme(scheme)

        while True:
            self.dialog_trigger_signal.emit()
            loop = QtCore.QEventLoop()
            # noinspection PyUnresolvedReferences
            self.dialog.dialog_done_signal.connect(loop.quit)
            loop.exec_()
            if self.dialog.exit_status():
                self.session.set_trial_info(self.dialog.get_values())
                break
            else:
                continue
        self.video_out_filename = self.session.get_video_file_name_for_trial()
        self.open_files()

        width, height = self.frame_size
        self.splash_screen_countdown = self.fps * 3  # show the splash screen for three seconds
        self.splash_screen = np.zeros((height, width, 3), np.uint8)

        trial_info = self.session.get_trial_info()
        font = cv2.FONT_HERSHEY_DUPLEX
        str1 = "Session " + str(trial_info['session']) + "  Trial " + str(trial_info['trial_nr'])
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

    def add_trial(self):
        if self.session:
            self.session.add_trial()
            self.dialog.set_scheme(self.session.get_scheme_trial_info())
            self.dialog.set_readonly(False)

    def skip_trial(self):
        if self.session:
            self.session.skip_trial()
            self.dialog.set_scheme(self.session.get_scheme_trial_info())

    @QtCore.pyqtSlot()
    def start_acquisition(self):
        if self.session:
            self.trial_setup()
        if self.can_acquire:
            # 1. ask for confirmation of trial parameters
            # 2. make up new video file
            # 3. make up splash screen
            if self.acquiring:  # must be paused
                self.paused = False
                self.is_acquiring_signal.emit(True)
            else:
                self.acquiring = True
                if not self.capturing:
                    self.capturing = True

    @QtCore.pyqtSlot()
    def stop_acquisition(self):
        self.acquiring = False
        if self.session:
            self.session.close()
            self.session = None

    @QtCore.pyqtSlot(bool)
    def set_mirror(self, mirrored):
        self.mirrored = mirrored

    @QtCore.pyqtSlot(int)
    def set_rotate(self, i):
        self.rotate_angle = self.rotate_options[i]
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
        self.open_files()
        if not self.session:
            self.open_csv_files()

    def open_files(self):
        filename = self.video_out_filename
        print("opening output file: ", filename, "...")
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
            self.can_acquire = True
            print("Success")
        else:
            import warnings
            warnings.warn("Can't open output file!!")

    def close_files(self):
        if self.out:
            self.out.release()
            self.out = None
        if self.raw_out:
            self.raw_out.release()
            self.raw_out = None

    def open_csv_files(self):
        filename_csv = self.make_csv_filename(self.video_out_filename)
        self.csv_out = open(filename_csv, 'w')

    @staticmethod
    def make_raw_filename(video_filename):
        import os
        dirname = os.path.dirname(video_filename)
        basename, _ = os.path.splitext(os.path.basename(video_filename))
        filename = os.path.join(dirname, basename + '_raw.avi')
        return filename

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

    @QtCore.pyqtSlot()
    def query_frame(self):
        pass  # pure virtual function

    def add_timestamp_string(self, frame):
        if self.acquiring and self.display_time:
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
        return datetime.timedelta(0)

    @QtCore.pyqtSlot()
    def cleanup(self):
        self.can_acquire = False
        self.to_release = True
        if self.thread:
            self.thread.wait()

    def release(self):
        print("releasing camera and stopping")
        time.sleep(0.5)
        # if self._device:
        #     self._device.release()
        if self.out:
            self.out.release()
            self.out = None
        if self.csv_out:
            self.csv_out.close()
        if self.thread:
            self.thread.quit()

    @QtCore.pyqtSlot()
    def set_paused(self):
        if self.session:
            self.close_files()
            self.session.set_trial_finished()

        self.paused = True

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, p):
        self.is_paused_signal.emit(p)
        self._paused = p

    @property
    def frame_size(self):
        return None  # pure virtual

    @property
    def fps(self):
        return 0  # pure virtual

    # the following definitions are the business logic of the experiment,
    # they may be overridden for a different experiment

    dir_keys = {QtCore.Qt.Key_U: 'UL', QtCore.Qt.Key_O: 'UR',
                QtCore.Qt.Key_J: 'LL', QtCore.Qt.Key_L: 'LR',
                QtCore.Qt.Key_T: 'TR'}

    rect_coord = {'UL': (lambda w, h: ((8, 8), (int(w*0.3), int(h*0.3)))),
                  'UR': (lambda w, h: ((w-8, 8), (int(w*0.7), int(h*0.3)))),
                  'LL': (lambda w, h: ((8, h-8), (int(w*0.3), int(h*0.7)))),
                  'LR': (lambda w, h: ((w-8, h-8), (int(w*0.7), int(h*0.7))))}

    def init_obj_state(self):
        self.obj_state = {'UL': 0, 'UR': 0, 'LR': 0, 'LL': 0, 'TR': 0}

    @QtCore.pyqtSlot(str)
    def obj_state_change(self, msg):

        if self.session and not self.trial_ready:
            return
        if msg == 'TR0':
            return
        if msg == 'TR1':
            trial_on = 1 - self.obj_state['TR']
            self.obj_state['TR'] = trial_on
            msg = 'TR' + str(trial_on)
            if trial_on:
                self.trial_ongoing = True
                if self.session:
                    self.start_time = datetime.datetime.now()
            else:
                self.trial_ongoing = False
        else:
            if self.session and not self.trial_ongoing:
                return
            if msg[:-1] in self.rect_coord and msg[-1] == '1':
                self.obj_state[msg[:-1]] = 1
            else:
                self.obj_state[msg[:-1]] = 0

        if self.acquiring and self.capturing:
            t = self.get_cur_time()
            ts = t.seconds + 1.e-6 * t.microseconds
            if self.session:
                self.session.set_event(ts, self.frame_no, msg)
            elif self.csv_out:
                self.csv_out.write("{},{},{}\n".format(ts, self.frame_no, msg))

    def process_frame(self, frame):
        h, w, _ = frame.shape
        for place, state in self.obj_state.items():
            if place in self.rect_coord and state:
                pt1, pt2 = self.rect_coord[place](w, h)
                cv2.rectangle(frame, pt1, pt2, (0, 0, 255), 2)
        if self.obj_state['TR']:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 0), 8)
        self.add_timestamp_string(frame)


class VideoDeviceManager(DeviceManager):
    video_finished_signal = QtCore.pyqtSignal(name="CameraDevice.video_finished_signal")
    frame_pos_signal = QtCore.pyqtSignal(int, name="CameraDevice.frame_pos_signal")

    def __init__(self, video_file=None, parent=None, session_file=None):
        self.video_file = video_file
        super(VideoDeviceManager, self).__init__(parent=parent, session_file=session_file)
        self.init_thread()

    def init_device(self):
        # noinspection PyArgumentList
        cd = cv2.VideoCapture(self.video_file)
        if not cd.isOpened():
            raise RuntimeError("Could not open video file {}".format(self.video_file))
        self.query_frame()
        return cd

    def video_last_frame(self):
        return self._device.get(cv2.CAP_PROP_FRAME_COUNT)

    @QtCore.pyqtSlot()
    def query_frame(self):
        if not self.capturing:
            return
        if not self.paused and self.acquiring:
            ret, frame = self._device.read()
            if ret:
                self.frame_no = int(self._device.get(cv2.CAP_PROP_POS_FRAMES))
                self.frame_pos_signal.emit(self.frame_no)
                h, w, _ = frame.shape
                if self.save_raw_video and self.raw_out and self.acquiring:
                    self.raw_out.write(frame)
                self.process_frame(frame)

                if self.out and self.acquiring:
                    self.out.write(frame)
                self.new_frame.emit(frame)
            else:
                self.video_finished_signal.emit()
                self.paused = True
        if self.to_release:
            self.release()

    @property
    def frame_size(self):
        w = int(self._device.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._device.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return int(w), int(h)

    @QtCore.pyqtSlot(int)
    def skip_to_frame(self, val):
        self._device.set(cv2.CAP_PROP_POS_FRAMES, float(val))

    @property
    def fps(self):
        fps = int(self._device.get(cv2.CAP_PROP_FPS))
        return fps

    def get_cur_time(self):
        return datetime.timedelta(milliseconds=self._device.get(cv2.CAP_PROP_POS_MSEC))

    def set_session(self, filename):
        try:
            self.session = VideoSessionManager(filename)
            self.session_set_signal.emit(True)
        except ValueError as e:
            import warnings
            warnings.warn(str(e))
            self.session = None
            self.session_set_signal.emit(False)


class CameraDeviceManager(DeviceManager):
    _DEFAULT_FPS = 30

    def __init__(self, camera_id=0, parent=None, session_file=None):
        self.camera_id = camera_id
        super(CameraDeviceManager, self).__init__(parent=parent, session_file=session_file)
        self.init_thread()
        self.paused = False

    def init_device(self):
        # noinspection PyArgumentList
        cd = cv2.VideoCapture(self.camera_id)
        if not cd.isOpened():
            raise RuntimeError("Could not initialize camera id {}".format(self.camera_id))
        return cd

    @QtCore.pyqtSlot()
    def query_frame(self):
        if self.to_release:
            self.release()
        if not self.capturing:
            return
        if not self.paused:
            if self.splash_screen_countdown:
                frame = self.splash_screen
                ret = True
                if self.splash_screen_countdown == 1:
                    self.trial_ready = True
                self.splash_screen_countdown -= 1
            else:
                ret, frame = self._device.read()
                if ret:
                    h, w, _ = frame.shape
                    frame = cv2.resize(frame, (int(w * self.scale), int(h * self.scale)), interpolation=cv2.INTER_AREA)
                    frame = self.rotate_functions[self.rotate_angle](frame)
                    if self.mirrored:
                        frame = cv2.flip(frame, 1)
            if ret:
                self.frame_no += 1
                if self.save_raw_video and self.raw_out and self.acquiring:
                    self.raw_out.write(frame)
                if self.splash_screen_countdown == 0:
                    self.process_frame(frame)

                if self.out and self.acquiring:
                    self.out.write(frame)
                self.new_frame.emit(frame)
            # else:
                #  notify that camera is not acquiring ?
                # self.video_finished_signal.emit()
                # self.paused = True

    @property
    def frame_size(self):
        w = int(self._device.get(cv2.CAP_PROP_FRAME_WIDTH) * self.scale)
        h = int(self._device.get(cv2.CAP_PROP_FRAME_HEIGHT) * self.scale)
        if self.rotate_angle in (90, 270):
            w, h = h, w
        return int(w), int(h)

    @property
    def fps(self):
        fps = self._DEFAULT_FPS
        return fps

    def get_cur_time(self):
        if self.session:
            if not self.trial_ongoing:
                return datetime.timedelta(0)
            else:
                return datetime.datetime.now() - self.start_time
        else:
            return datetime.datetime.now() - self.start_time

    def set_session(self, filename):
        try:
            # noinspection PyUnresolvedReferences,PyCallByClass,PyTypeChecker
            init_trial, ok = QtWidgets.QInputDialog.getInt(None,
                                                           "Initial trial",
                                                           "Please enter the first scheme trial for this session",
                                                           1, min=1, flags=QtCore.Qt.WindowFlags())
            if not ok:
                init_trial = 1
            self.session = LiveSessionManager(filename, initial_trial=init_trial)
            self.session_set_signal.emit(True)
            self.can_acquire = True

        except ValueError as e:
            self.session = None
            self.session_set_signal.emit(False)
            import warnings
            warnings.warn(str(e))


class CameraWidget(QtWidgets.QWidget):
    new_frame = QtCore.pyqtSignal(np.ndarray, name="CameraWidget.new_frame")
    key_action = QtCore.pyqtSignal(str, name="CameraWidget.key_action")

    def __init__(self, parent=None, flags=None):
        if flags:
            flags_ = flags
        else:
            # noinspection PyUnresolvedReferences
            flags_ = QtCore.Qt.WindowFlags()
        super(CameraWidget, self).__init__(parent, flags=flags_)
        self._camera_device = None
        self._frame = None
        self.setMinimumSize(640, 360)
        self.setMaximumSize(640, 360)

    def set_device(self, camera_device):
        if camera_device:
            self._camera_device = camera_device
            self._camera_device.new_frame.connect(self._on_new_frame)
            # w, h = self._camera_device.frame_size
            # self.setMinimumSize(w, h)
            # self.setMaximumSize(w, h)
            self._camera_device.size_changed_signal.connect(self.size_changed)

    @QtCore.pyqtSlot()
    def size_changed(self):
        w, h = self._camera_device.frame_size
        self.setMinimumSize(w, h)  # TODO rescale so that it fits in maximum size
        self.setMaximumSize(w, h)
        self.updateGeometry()

    def sizeHint(self):
        if self._camera_device:
            w, h = self._camera_device.frame_size
            return QtCore.QSize(w, h)
        else:
            return QtCore.QSize(800, 600)

    @QtCore.pyqtSlot(np.ndarray)
    def _on_new_frame(self, frame):
        self._frame = frame.copy()
        self.new_frame.emit(self._frame)
        self.update()

    def changeEvent(self, e):
        if self._camera_device is not None and e.type() == QtCore.QEvent.EnabledChange:
            if self.isEnabled():
                self._camera_device.new_frame.connect(self._on_new_frame)
            else:
                self._camera_device.new_frame.disconnect(self._on_new_frame)

    def paintEvent(self, e):
        if self._frame is None:
            painter = QtGui.QPainter(self)
            painter.fillRect(self.rect(), QtCore.Qt.green)
            return
        painter = QtGui.QPainter(self)
        painter.drawImage(QtCore.QPoint(0, 0), OpenCVQImage(self._frame))

    def keyPressEvent(self, event):
        if not event.isAutoRepeat() and event.key() in DeviceManager.dir_keys:
            msg = DeviceManager.dir_keys[event.key()] + '1'
            self.key_action.emit(msg)
        event.accept()

    def keyReleaseEvent(self, event):
        if event.key() in DeviceManager.dir_keys:
            msg = DeviceManager.dir_keys[event.key()] + '0'
            self.key_action.emit(msg)
        event.accept()
