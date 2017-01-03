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


class CameraDevice(QtCore.QObject):
    _DEFAULT_FPS = 15

    new_frame = QtCore.pyqtSignal(np.ndarray, name="CameraDevice.new_frame")
    can_acquire_signal = QtCore.pyqtSignal(bool, name="CameraDevice.can_acquire_signal")
    is_acquiring_signal = QtCore.pyqtSignal(bool, name="CameraDevice.is_acquiring_signal")
    is_paused_signal = QtCore.pyqtSignal(bool, name="CameraDevice.is_paused_signal")

    def __init__(self, camera_id=0, mirrored=False, video_file=None, parent=None):
        super(CameraDevice, self).__init__(parent)

        self.obj_state = {'UL': 0, 'UR': 0, 'LR': 0, 'LL': 0}
        self.mirrored = mirrored

        if video_file:
            pass  # TODO implement video
        else:
            # noinspection PyArgumentList
            self._cameraDevice = cv2.VideoCapture(camera_id)
            if not self._cameraDevice.isOpened():
                raise RuntimeError("Could not initialize camera id {}".format(camera_id))
        self._timer = QtCore.QTimer(self)
        self.start_time = datetime.datetime.now()
        # noinspection PyUnresolvedReferences
        self._timer.timeout.connect(self._query_frame)
        self._timer.setInterval(1000 / self.fps)
        self.paused = False
        self.out = None
        self._can_acquire = False
        self._acquiring = False
        self.to_release = False
        self.thread = QtCore.QThread()
        self.moveToThread(self.thread)
        self.thread.start()

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

    @QtCore.pyqtSlot()
    def stop_acquisition(self):
        self.acquiring = False

    @QtCore.pyqtSlot(bool)
    def set_mirror(self, mirrored):
        self.mirrored = mirrored

    @QtCore.pyqtSlot(str)
    def set_out_video_file(self, filename):
        if self.out:
            self.out.release()
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(filename, fourcc, self.fps, self.frame_size)
        if self.out.isOpened():
            self.can_acquire = True
        # TODO open CSV file for scoring save

    @QtCore.pyqtSlot()
    def _query_frame(self):
        ret, frame = self._cameraDevice.read()
        h, w, _ = frame.shape
        frame = cv2.resize(frame, (int(w/2), int(h/2)), interpolation=cv2.INTER_AREA)

        if self.mirrored:
            frame = cv2.flip(frame, 1)

        self.process_frame(frame)

        if self.out and self.acquiring:
            self.out.write(frame)
        self.new_frame.emit(frame)
        if self.to_release:
            self.release()

    def add_timestamp_string(self, frame):
        if self.acquiring:
            h, w, _ = frame.shape
            cur_time = str(datetime.datetime.now() - self.start_time)[:-4]
            font = cv2.FONT_HERSHEY_DUPLEX
            # noinspection PyUnusedLocal
            t_size, baseline = cv2.getTextSize(cur_time, font, 0.5, 1)
            tpt = 5, h - 5
            cv2.putText(frame, cur_time, tpt, font, 0.5, (0, 0, 255), 1)

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
            # TODO close CSV file
        if self.thread:
            self.thread.quit()

    @QtCore.pyqtSlot()
    def set_paused(self):
        self.paused = True

    @property
    def paused(self):
        return not self._timer.isActive()

    @paused.setter
    def paused(self, p):
        self.is_paused_signal.emit(p)
        if p:
            self._timer.stop()
        else:
            self._timer.start()

    @property
    def frame_size(self):
        w = int(self._cameraDevice.get(cv2.CAP_PROP_FRAME_WIDTH)/2)
        h = int(self._cameraDevice.get(cv2.CAP_PROP_FRAME_HEIGHT)/2)
        return int(w), int(h)

    @property
    def fps(self):
        fps = 15
        # fps = int(self._camera_device.get(cv2.CAP_PROP_FPS))
        # if not fps > 0:
        #     fps = self._DEFAULT_FPS
        return fps

    # the following definitions are the business logic of the experiment,
    # they may be overriden for a different experiment

    dir_keys = {QtCore.Qt.Key_U: 'UL', QtCore.Qt.Key_O: 'UR', QtCore.Qt.Key_J: 'LL', QtCore.Qt.Key_L: 'LR'}
    rect_coord = {'UL': (lambda w, h: ((3, 3), (int(w*0.3), int(h*0.3)))),
                  'UR': (lambda w, h: ((w-3, 3), (int(w*0.7), int(h*0.3)))),
                  'LL': (lambda w, h: ((3, h-3), (int(w*0.3), int(h*0.7)))),
                  'LR': (lambda w, h: ((w-3, h-3), (int(w*0.7), int(h*0.7))))}

    @QtCore.pyqtSlot(str)
    def obj_state_change(self, msg):
        if msg[:-1] in self.rect_coord and msg[-1] == '1':
            self.obj_state[msg[:-1]] = 1
        else:
            self.obj_state[msg[:-1]] = 0

        if self.acquiring and self._timer.isActive():
            pass  # TODO write to file

    def process_frame(self, frame):
        h, w, _ = frame.shape
        for place, state in self.obj_state.items():
            if state:
                pt1, pt2 = self.rect_coord[place](w, h)
                cv2.rectangle(frame, pt1, pt2, (0, 0, 255), 2)
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
            print(w, h)
            self.setMinimumSize(w, h)
            self.setMaximumSize(w, h)

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
