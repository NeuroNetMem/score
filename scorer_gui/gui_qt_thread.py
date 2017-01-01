import cv2
import numpy as np
import time
import datetime

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


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
    dir_keys = {QtCore.Qt.Key_U: 'UL', QtCore.Qt.Key_O: 'UR', QtCore.Qt.Key_J: 'LL', QtCore.Qt.Key_L: 'LR'}
    rect_coord = {'UL': (lambda w, h: ((3, 3), (int(w*0.3), int(h*0.3)))),
                  'UR': (lambda w, h: ((w-3, 3), (int(w*0.7), int(h*0.3)))),
                  'LL': (lambda w, h: ((3, h-3), (int(w*0.3), int(h*0.7)))),
                  'LR': (lambda w, h: ((w-3, h-3), (int(w*0.7), int(h*0.7))))}

    def __init__(self, camera_id=0, mirrored=False, parent=None):
        super(CameraDevice, self).__init__(parent)

        self.obj_state = {'UL': 0, 'UR': 0, 'LR': 0, 'LL': 0}
        self.mirrored = mirrored

        # noinspection PyArgumentList
        self._cameraDevice = cv2.VideoCapture(camera_id)

        self._timer = QtCore.QTimer(self)
        self.start_time = datetime.datetime.now()
        # noinspection PyUnresolvedReferences
        self._timer.timeout.connect(self._query_frame)
        self._timer.setInterval(1000 / self.fps)
        self.paused = False
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter('~/output.avi', fourcc, self.fps, self.frame_size)
        self.thread = None
        self.to_release = False

    @QtCore.pyqtSlot()
    def _query_frame(self):
        ret, frame = self._cameraDevice.read()
        h, w, _ = frame.shape
        frame = cv2.resize(frame, (int(w/2), int(h/2)), interpolation=cv2.INTER_AREA)
        h, w, _ = frame.shape
        if self.mirrored:
            frame = cv2.flip(frame, 1)
        for place, state in self.obj_state.items():
            if state:
                pt1, pt2 = self.rect_coord[place](w, h)
                cv2.rectangle(frame, pt1, pt2, (0, 0, 255), 2)
        cur_time = str(datetime.datetime.now() - self.start_time)[:-4]
        font = cv2.FONT_HERSHEY_DUPLEX
        # noinspection PyUnusedLocal
        t_size, baseline = cv2.getTextSize(cur_time, font, 0.5, 1)
        tpt = 5, h - 5
        cv2.putText(frame, cur_time, tpt, font, 0.5, (0, 0, 255), 1)
        self.out.write(frame)
        self.new_frame.emit(frame)
        if self.to_release:
            self.release()

    @QtCore.pyqtSlot()
    def cleanup(self):
        self.to_release = True

    def release(self):
        print("releasing camera and stopping")
        self._timer.stop()
        time.sleep(0.5)
        self.out.release()
        self.out = None
        if self.thread:
            self.thread.quit()

    @QtCore.pyqtSlot(str)
    def obj_state_change(self, msg):
        if msg[-1] == '1':
            self.obj_state[msg[:-1]] = 1
        else:
            self.obj_state[msg[:-1]] = 0

    @property
    def paused(self):
        return not self._timer.isActive()

    @paused.setter
    def paused(self, p):
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
        # fps = int(self._cameraDevice.get(cv2.CAP_PROP_FPS))
        # if not fps > 0:
        #     fps = self._DEFAULT_FPS
        return fps


class CameraWidget(QtWidgets.QWidget):
    new_frame = QtCore.pyqtSignal(np.ndarray, name="CameraWidget.new_frame")
    key_action = QtCore.pyqtSignal(str, name="CameraWidget.key_action")

    def __init__(self, camera_device, parent=None, flags=None):
        if flags:
            flags_ = flags
        else:
            # noinspection PyUnresolvedReferences
            flags_ = QtCore.Qt.WindowFlags()
        super(CameraWidget, self).__init__(parent, flags=flags_)

        self._frame = None

        self._cameraDevice = camera_device
        self._cameraDevice.new_frame.connect(self._on_new_frame)

        w, h = self._cameraDevice.frame_size
        self.setMinimumSize(w, h)
        self.setMaximumSize(w, h)

    @QtCore.pyqtSlot(np.ndarray)
    def _on_new_frame(self, frame):
        self._frame = frame.copy()
        self.new_frame.emit(self._frame)
        self.update()

    def changeEvent(self, e):
        if e.type() == QtCore.QEvent.EnabledChange:
            if self.isEnabled():
                self._cameraDevice.new_frame.connect(self._on_new_frame)
            else:
                self._cameraDevice.new_frame.disconnect(self._on_new_frame)

    def paintEvent(self, e):
        if self._frame is None:
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
    thread1 = QtCore.QThread()
    camera_device.thread = thread1

    def close_all():
        camera_device.cleanup()
        thread1.wait()
        sys.exit()

    app.quitOnLastWindowClosed = False
    # noinspection PyUnresolvedReferences
    app.lastWindowClosed.connect(close_all)
    camera_device.moveToThread(thread1)
    thread1.start()

    camera_widget2 = CameraWidget(camera_device)
    # noinspection PyUnresolvedReferences
    camera_widget2.key_action.connect(camera_device.obj_state_change)
    camera_widget2.show()

    app.exec_()

if __name__ == '__main__':
    _main()
