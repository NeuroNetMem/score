from PyQt5 import QtWidgets
from PyQt5 import QtCore
from scorer_gui.obj_scorer_ui import Ui_MainWindow
from scorer_gui.gui_qt_thread import CameraDevice, find_how_many_cameras


class ScorerMainWindow(QtWidgets.QMainWindow):
    key_action = QtCore.pyqtSignal(str, name="ScorerMainWindow.key_action")

    def __init__(self):
        # noinspection PyUnresolvedReferences
        flags_ = QtCore.Qt.WindowFlags()
        super(ScorerMainWindow, self).__init__(flags=flags_)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setMenuBar(self.ui.menubar)
        self._device = None
        self.ui.actionQuit.triggered.connect(self.close_all)
        self.ui.actionOpen_Camera.triggered.connect(self.get_camera_id_to_open)
        self.ui.actionSave_to.triggered.connect(self.get_save_video_file)

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, dev):
        self._device = dev
        if dev:
            # noinspection PyUnresolvedReferences
            self.key_action.connect(self._device.obj_state_change)
            self.ui.mirroredButton.setEnabled(True)
            self.ui.mirroredButton.toggled.connect(self.device.set_mirror)
            self.device.can_acquire_signal.connect(self.change_acquisition_state)
            self.device.is_acquiring_signal.connect(self.acquisition_started_stopped)
            self.device.is_paused_signal.connect(self.has_paused)
            self.ui.playButton.clicked.connect(self.device.start_acquisition)
            self.ui.pauseButton.clicked.connect(self.device.set_paused)
            self.ui.stopButton.clicked.connect(self.device.stop_acquisition)

        self.ui.cameraWidget.set_device(self.device)

    @QtCore.pyqtSlot(bool)
    def change_acquisition_state(self, can_acquire):
        self.ui.playButton.setEnabled(can_acquire)
        if can_acquire:
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)

    @QtCore.pyqtSlot(bool)
    def acquisition_started_stopped(self, val):
        self.ui.playButton.setEnabled(False)
        if val:
            self.ui.pauseButton.setEnabled(True)
            self.ui.stopButton.setEnabled(True)
        else:
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)

    @QtCore.pyqtSlot(bool)
    def has_paused(self, val):
        if val:
            self.ui.playButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(True)
        else:
            self.ui.playButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(True)
            self.ui.stopButton.setEnabled(True)

    @QtCore.pyqtSlot()
    def close_all(self):
        import sys
        if self.device:
            self.device.cleanup()
        sys.exit()

    @QtCore.pyqtSlot()
    def get_camera_id_to_open(self):
        n_cameras = find_how_many_cameras()
        ops = [str(i) for i in range(n_cameras)]
        # noinspection PyCallByClass,PyTypeChecker,PyArgumentList
        dialog_out = QtWidgets.QInputDialog.getItem(self, "Open Camera", "Which camera id do you want to open?", ops)
        if not dialog_out[1]:
            return
        self.set_camera(int(dialog_out[0]))

    # noinspection PyArgumentList
    @QtCore.pyqtSlot()
    def get_save_video_file(self):
        import os
        # noinspection PyCallByClass,PyTypeChecker
        dialog_out = QtWidgets.QFileDialog.getSaveFileName(self, "Save Video File",
                                                           os.path.join(os.getcwd(), 'untitled.avi'),
                                                           "Videos (*.avi)")
        save_video_file = dialog_out[0]
        if save_video_file:
            self.device.set_out_video_file(save_video_file)
            self.ui.destLabel.setText(os.path.basename(save_video_file))

    def set_camera(self, camera_id):
        if self.device:
            self.device.cleanup()
        self.device = CameraDevice(camera_id=camera_id, mirrored=False)
        self.ui.sourceLabel.setText("Camera: " + str(camera_id))

    def keyPressEvent(self, event):
        if self.device:
            if not event.isAutoRepeat() and event.key() in self.device.dir_keys:
                msg = CameraDevice.dir_keys[event.key()] + '1'
                self.key_action.emit(msg)
        event.accept()

    def keyReleaseEvent(self, event):
        if self.device:
            if event.key() in self.device.dir_keys:
                msg = CameraDevice.dir_keys[event.key()] + '0'
                self.key_action.emit(msg)
        event.accept()


def _main():
    import sys
    app = QtWidgets.QApplication(sys.argv)

    window = ScorerMainWindow()
    # window.device = CameraDevice(mirrored=True)
    window.show()
    app.quitOnLastWindowClosed = False
    # noinspection PyUnresolvedReferences
    app.lastWindowClosed.connect(window.close_all)
    app.exec_()


if __name__ == '__main__':
    _main()
