import cv2
import numpy as np

from PyQt4 import QtCore
from PyQt4 import QtGui


class OpenCVQImage(QtGui.QImage):
    def __init__(self, opencv_bgr_img):

        h, w, n_channels = opencv_bgr_img.shape
        depth = opencv_bgr_img.dtype
        if depth != np.uint8 or n_channels != 3:
            raise ValueError("the input image must be 8-bit, 3-channel")

        # it's assumed the image is in BGR format
        img2 = cv2.resize(opencv_bgr_img, (int(w/2), int(h/2)), interpolation=cv2.INTER_AREA)
        opencv_rgb_img = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)
        self._imgData = opencv_rgb_img.tostring()
        super(OpenCVQImage, self).__init__(self._imgData, int(w/2), int(h/2),
                                           QtGui.QImage.Format_RGB888)


class CameraDevice(QtCore.QObject):
    _DEFAULT_FPS = 15

    new_frame = QtCore.pyqtSignal(np.ndarray)
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
        # noinspection PyUnresolvedReferences
        self._timer.timeout.connect(self._query_frame)
        self._timer.setInterval(1000 / self.fps)
        print(self.fps)
        self.paused = False

    @QtCore.pyqtSlot()
    def _query_frame(self):
        ret, frame = self._cameraDevice.read()
        h, w, _ = frame.shape
        if self.mirrored:
            frame = cv2.flip(frame, 1)
            for place, state in self.obj_state.items():
                if state:
                    pt1, pt2 = self.rect_coord[place](w, h)
                    cv2.rectangle(frame, pt1, pt2, (0, 0, 255), 2)
        self.new_frame.emit(frame)

    @QtCore.pyqtSlot(str)
    def obj_state_change(self, msg):
        if msg[-1] == '1':
            self.obj_state[msg[:-1]] = 1
            print('rect', msg[:-1], 'on')
        else:
            self.obj_state[msg[:-1]] = 0
            print('rect', msg[:-1], 'off')


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
        w = self._cameraDevice.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = self._cameraDevice.get(cv2.CAP_PROP_FRAME_HEIGHT)
        return int(w), int(h)

    @property
    def fps(self):
        fps = 15
        # fps = int(self._cameraDevice.get(cv2.CAP_PROP_FPS))
        # if not fps > 0:
        #     fps = self._DEFAULT_FPS
        return fps


class CameraWidget(QtGui.QWidget):
    new_frame = QtCore.pyqtSignal(np.ndarray)
    key_action = QtCore.pyqtSignal(str)

    def __init__(self, camera_device, parent=None):
        super(CameraWidget, self).__init__(parent)

        self._frame = None

        self._cameraDevice = camera_device
        self._cameraDevice.new_frame.connect(self._on_new_frame)

        w, h = self._cameraDevice.frame_size
        w = int(w/2)
        h = int(h/2)
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
            # print("pressed:", event.text())
            event.accept()

    def keyReleaseEvent(self, event):
        if event.key() in CameraDevice.dir_keys:
            msg = CameraDevice.dir_keys[event.key()] + '0'
            self.key_action.emit(msg)
            # print("released:", event.text())
            event.accept()


def _main():
    @QtCore.pyqtSlot(np.ndarray)
    def on_new_frame(frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR, frame)
        msg = "processed frame"
        font = cv2.FONT_HERSHEY_DUPLEX
        t_size, baseline = cv2.getTextSize(msg, font, 1, 1)
        h, w, _ = frame.shape
        tpt = int((w - t_size[0]) / 2), int((h - t_size[1]) / 2)
        cv2.putText(frame, msg, tpt, font, 1, (255, 0, 0), 1)

    import sys

    app = QtGui.QApplication(sys.argv)

    camera_device = CameraDevice(mirrored=True)

    # camera_widget1 = CameraWidget(camera_device)
    # camera_widget1.new_frame.connect(on_new_frame)
    # camera_widget1.show()

    camera_widget2 = CameraWidget(camera_device)
    camera_widget2.key_action.connect(camera_device.obj_state_change)
    camera_widget2.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    _main()
