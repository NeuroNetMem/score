# noinspection PyPackageRequirements
import cv2
import numpy as np
import time
import datetime

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


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


# the camera model for the Camera acquisition
class CameraDevice(QtCore.QObject):
    _DEFAULT_FPS = 15

    new_frame = QtCore.pyqtSignal(np.ndarray, name="CameraDevice.new_frame")
    can_acquire_signal = QtCore.pyqtSignal(bool, name="CameraDevice.can_acquire_signal")
    is_acquiring_signal = QtCore.pyqtSignal(bool, name="CameraDevice.is_acquiring_signal")
    is_paused_signal = QtCore.pyqtSignal(bool, name="CameraDevice.is_paused_signal")
    from_video_signal = QtCore.pyqtSignal(bool, name="CameraDevice.from_video_signal")
    video_finished_signal = QtCore.pyqtSignal(name="CameraDevice.video_finished_signal")
    frame_pos_signal = QtCore.pyqtSignal(int, name="CameraDevice.frame_pos_signal")
    size_changed_signal = QtCore.pyqtSignal(name="CameraDevice.size_changed_signal")

    scales_possible = ['0.5', '0.8', '1', '1.5', '2']
    scale_init = 1

    def __init__(self, camera_id=0, mirrored=False, video_file=None, parent=None, session=None):
        super(CameraDevice, self).__init__(parent)

        self.obj_state = {}
        self.init_obj_state()
        self.mirrored = mirrored
        self.session = session
        self._from_video = False
        self.display_time = True
        self.save_raw_video = True
        self.filename = None
        self.out = None
        self.raw_out = None
        self.csv_out = None
        self.scale = float(self.scales_possible[self.scale_init])
        self._can_acquire = False
        self._acquiring = False
        self._paused = False
        self.to_release = False
        if video_file:
            # noinspection PyArgumentList
            self._cameraDevice = cv2.VideoCapture(video_file)
            if not self._cameraDevice.isOpened():
                raise RuntimeError("Could not open video file {}".format(video_file))
            self.from_video = True
        else:
            # noinspection PyArgumentList
            self._cameraDevice = cv2.VideoCapture(camera_id)
            if not self._cameraDevice.isOpened():
                raise RuntimeError("Could not initialize camera id {}".format(camera_id))
            self.from_video = False

        self._timer = QtCore.QTimer(self)
        # noinspection PyUnresolvedReferences
        self._timer.timeout.connect(self._query_frame)
        self._timer.setInterval(1000 / self.fps)
        if not self.from_video:
            self._timer.start()
        self.paused = False
        if self.from_video:
            self._query_frame()
        self.start_time = datetime.datetime.now()
        self.frame_no = 0

        self.thread = QtCore.QThread()
        self.moveToThread(self.thread)
        self.thread.start()

    @QtCore.pyqtSlot(int)
    def change_scale(self, i):
        self.scale = float(self.scales_possible[i])
        self.size_changed_signal.emit()

    @property
    def from_video(self):
        return self._from_video

    @from_video.setter
    def from_video(self, val):
        self._from_video = val
        self.from_video_signal.emit(val)

    def video_last_frame(self):
        if self.from_video:
            return self._cameraDevice.get(cv2.CAP_PROP_FRAME_COUNT)

    @QtCore.pyqtSlot(int)
    def skip_to_frame(self, val):
        if self.from_video:
            self._cameraDevice.set(cv2.CAP_PROP_POS_FRAMES, float(val))

    @property
    def can_acquire(self):
        return self._can_acquire

    @can_acquire.setter
    def can_acquire(self, val):
        self._can_acquire = val
        self.can_acquire_signal.emit(val)

    @property
    def acquiring(self):
        return self._acquiring

    @acquiring.setter
    def acquiring(self, val):
        if val:
            self.start_time = datetime.datetime.now()
            self.frame_no = 0
        self._acquiring = val
        self.is_acquiring_signal.emit(val)

    @QtCore.pyqtSlot()
    def start_acquisition(self):
        if self.can_acquire:

            if self.acquiring:  # must be paused
                self.paused = False
                self.is_acquiring_signal.emit(True)
            else:
                self.acquiring = True
                if not self._timer.isActive():
                    self._timer.start()

    @QtCore.pyqtSlot()
    def stop_acquisition(self):
        self.acquiring = False

    @QtCore.pyqtSlot(bool)
    def set_mirror(self, mirrored):
        self.mirrored = mirrored

    @QtCore.pyqtSlot(bool)
    def set_raw_out(self, val):
        self.save_raw_video = val

    @QtCore.pyqtSlot(bool)
    def set_display_time(self, val):
        self.display_time = val

    @QtCore.pyqtSlot(str)
    def set_out_video_file(self, filename):
        self.filename = filename
        self.open_files()

    def open_files(self):
        filename = self.filename
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
        filename_csv = self.make_csv_filename(filename)
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
    def _query_frame(self):
        if not self.paused and (not self.from_video or self.acquiring):
            ret, frame = self._cameraDevice.read()
            if ret:
                if self.from_video:
                    self.frame_no = int(self._cameraDevice.get(cv2.CAP_PROP_POS_FRAMES))
                    self.frame_pos_signal.emit(self.frame_no)
                else:
                    self.frame_no += 1
                h, w, _ = frame.shape
                if not self.from_video:
                    frame = cv2.resize(frame, (int(w*self.scale), int(h*self.scale)), interpolation=cv2.INTER_AREA)

                if self.mirrored:
                    frame = cv2.flip(frame, 1)
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
        if self.from_video:
            return datetime.timedelta(milliseconds=self._cameraDevice.get(cv2.CAP_PROP_POS_MSEC))
        else:
            return datetime.datetime.now() - self.start_time

    @QtCore.pyqtSlot()
    def cleanup(self):
        self.can_acquire = False
        self.to_release = True
        self.thread.wait()

    def release(self):
        print("releasing camera and stopping")
        self._timer.stop()
        time.sleep(0.5)
        # if self._cameraDevice:
        #     self._cameraDevice.release()
        if self.out:
            self.out.release()
            self.out = None
        if self.csv_out:
            self.csv_out.close()
        if self.thread:
            self.thread.quit()

    @QtCore.pyqtSlot()
    def set_paused(self):
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
        if self.from_video:
            w = int(self._cameraDevice.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cameraDevice.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else:
            w = int(self._cameraDevice.get(cv2.CAP_PROP_FRAME_WIDTH) * self.scale)
            h = int(self._cameraDevice.get(cv2.CAP_PROP_FRAME_HEIGHT) * self.scale)
        return int(w), int(h)

    @property
    def fps(self):
        fps = 15
        # fps = int(self._camera_device.get(cv2.CAP_PROP_FPS))
        # if not fps > 0:
        #     fps = self._DEFAULT_FPS
        return fps

    # the following definitions are the business logic of the experiment,
    # they may be overridden for a different experiment

    dir_keys = {QtCore.Qt.Key_U: 'UL', QtCore.Qt.Key_O: 'UR',
                QtCore.Qt.Key_J: 'LL', QtCore.Qt.Key_L: 'LR',
                QtCore.Qt.Key_T: 'TR'}

    rect_coord = {'UL': (lambda w, h: ((3, 3), (int(w*0.3), int(h*0.3)))),
                  'UR': (lambda w, h: ((w-3, 3), (int(w*0.7), int(h*0.3)))),
                  'LL': (lambda w, h: ((3, h-3), (int(w*0.3), int(h*0.7)))),
                  'LR': (lambda w, h: ((w-3, h-3), (int(w*0.7), int(h*0.7))))}

    def init_obj_state(self):
        self.obj_state = {'UL': 0, 'UR': 0, 'LR': 0, 'LL': 0, 'TR': 0}

    @QtCore.pyqtSlot(str)
    def obj_state_change(self, msg):
        if msg == 'TR0':
            return
        if msg == 'TR1':
            trial_on = 1 - self.obj_state['TR']
            self.obj_state['TR'] = trial_on
            msg = 'TR' + str(trial_on)
        else:
            if msg[:-1] in self.rect_coord and msg[-1] == '1':
                self.obj_state[msg[:-1]] = 1
            else:
                self.obj_state[msg[:-1]] = 0

        if self.csv_out and self.acquiring and self._timer.isActive():
            t = self.get_cur_time()
            ts = t.seconds + 1.e-6 * t.microseconds
            self.csv_out.write("{},{},{}\n".format(ts, self.frame_no, msg))

    def process_frame(self, frame):
        h, w, _ = frame.shape
        for place, state in self.obj_state.items():
            if place in self.rect_coord and state:
                pt1, pt2 = self.rect_coord[place](w, h)
                cv2.rectangle(frame, pt1, pt2, (0, 0, 255), 2)
        if self.obj_state['TR']:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 255, 0), 2)
        self.add_timestamp_string(frame)


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
            w, h = self._camera_device.frame_size
            self.setMinimumSize(w, h)
            self.setMaximumSize(w, h)
            self._camera_device.size_changed_signal.connect(self.size_changed)

    @QtCore.pyqtSlot()
    def size_changed(self):
        w, h = self._camera_device.frame_size
        self.setMinimumSize(w, h)
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
        if not event.isAutoRepeat() and event.key() in CameraDevice.dir_keys:
            msg = CameraDevice.dir_keys[event.key()] + '1'
            self.key_action.emit(msg)
        event.accept()

    def keyReleaseEvent(self, event):
        if event.key() in CameraDevice.dir_keys:
            msg = CameraDevice.dir_keys[event.key()] + '0'
            self.key_action.emit(msg)
        event.accept()


def _main():

    import sys

    app = QtWidgets.QApplication(sys.argv)

    camera_device = CameraDevice(mirrored=True)

    def close_all():
        camera_device.cleanup()
        sys.exit()

    app.quitOnLastWindowClosed = False
    # noinspection PyUnresolvedReferences
    app.lastWindowClosed.connect(close_all)

    camera_widget = CameraWidget()
    camera_widget.set_device(camera_device)
    # noinspection PyUnresolvedReferences
    camera_widget.key_action.connect(camera_device.obj_state_change)
    camera_widget.show()

    app.exec_()

if __name__ == '__main__':
    _main()
