from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

# noinspection PyUnresolvedReferences
import scorer_gui.obj_rc
from scorer_gui.obj_scorer_model import VideoDeviceManager, CameraDeviceManager, DeviceManager
from scorer_gui.obj_scorer_ui import Ui_MainWindow
from scorer_gui.trial_dialog_ui import Ui_TrialDialog


class TrialDialog(QtWidgets.QDialog):
    def __init__(self, caller=None, trial_params=None, locations=None):
        # noinspection PyUnresolvedReferences
        flags_ = QtCore.Qt.WindowFlags()
        super(TrialDialog, self).__init__(flags=flags_)
        self.ui = Ui_TrialDialog()
        self.ui.setupUi(self)
        self.ui.objectComboBox.currentIndexChanged.connect(self.update_object_change)
        if caller:
            self.ui.addTrialButton.clicked.connect(caller.add_trial)
            self.ui.skipTrialButton.clicked.connect(caller.skip_trial)
        if locations:
            self.ui.location1ComboBox.addItems(locations)
            self.ui.location2ComboBox.addItems(locations)
            self.locations = locations
        else:
            raise ValueError("missing argument locations")
        # object codes are derived by the filenames of the images in the resource file
        d = QtCore.QDir(':/obj_images')
        lst = d.entryList()
        self.obj_idxs = [int(s[:-4]) for s in lst]
        self.obj_idxs.sort()
        str_obj_idxs = [str(i) for i in self.obj_idxs]
        self.ui.objectComboBox.addItems(str_obj_idxs)

        self.set_values(trial_params)
        self.set_image()
        self.setWindowTitle("Next Trial")

    def set_image(self):
        try:
            obj_idx = self.get_current_object()
            # noinspection PyCallByClass,PyTypeChecker,PyArgumentList
            pixmap = QtGui.QPixmap(":/obj_images/" + str(obj_idx) + '.JPG')
            pixmap = pixmap.scaled(self.ui.objectLabel.size(), QtCore.Qt.KeepAspectRatio)
            self.ui.objectLabel.setPixmap(pixmap)
        except ValueError:
            print("object not in list!")

    def set_readonly(self, ro):
        self.ui.sessionLineEdit.setReadOnly(ro)
        self.ui.runLineEdit.setReadOnly(ro)
        self.ui.trialLineEdit.setReadOnly(ro)
        self.ui.subjectLineEdit.setReadOnly(ro)
        self.ui.subjectTrialLineEdit.setReadOnly(ro)
        self.ui.objectComboBox.setEnabled(not ro)
        self.ui.location1ComboBox.setEnabled(not ro)
        self.ui.location2ComboBox.setEnabled(not ro)

    # noinspection PyUnusedLocal
    @QtCore.pyqtSlot(int)
    def update_object_change(self, i):
        self.set_image()
        self.update()

    def get_current_object(self):
        return self.obj_idxs[self.ui.objectComboBox.currentIndex()]

    def set_values(self, values):
        print(values['trial'])
        self.ui.sessionLineEdit.setText(str(values['session']))
        self.ui.runLineEdit.setText(str(values['run_nr']))
        self.ui.trialLineEdit.setText(str(values['sequence_nr']))
        self.ui.subjectLineEdit.setText(str(values['subject']))
        self.ui.subjectTrialLineEdit.setText(str(values['trial']))
        self.ui.location1ComboBox.setCurrentIndex(self.locations.index(values['loc_1']))
        self.ui.location2ComboBox.setCurrentIndex(self.locations.index(values['loc_2']))
        self.ui.objectComboBox.setCurrentIndex(self.obj_idxs.index(values['obj']))
        px = self.make_location_map(values)
        self.ui.objLocLabel.setPixmap(px)

    def make_location_map(self, values):
        w = self.ui.objLocLabel
        p = QtGui.QPixmap(w.width(), w.height())
        p.fill(QtCore.Qt.white)
        width = w.width()
        height = w.height()

        sz = min(width, height) * 0.96

        painter = QtGui.QPainter()
        pen = QtGui.QPen()
        pen.setColor(QtCore.Qt.black)
        pen.setWidth(5)
        painter.begin(p)
        painter.setPen(pen)
        painter.drawRect(width * 0.02, height * 0.02, sz, sz)

        obj_rect = {
            'UL': QtCore.QRect(width * 0.1, height * 0.1, sz * 0.2, sz * 0.2),
            'UR': QtCore.QRect(width * 0.7, height * 0.1, sz * 0.2, sz * 0.2),
            'LL': QtCore.QRect(width * 0.1, height * 0.7, sz * 0.2, sz * 0.2),
            'LR': QtCore.QRect(width * 0.7, height * 0.7, sz * 0.2, sz * 0.2)}

        painter.setBrush(QtCore.Qt.black)
        painter.drawEllipse(obj_rect[values['loc_1']])
        painter.drawEllipse(obj_rect[values['loc_2']])
        painter.end()

        return p

    def get_values(self):
        values = {'session': int(self.ui.sessionLineEdit.text()), 'run_nr': int(self.ui.runLineEdit.text()),
                  'sequence_nr': int(self.ui.trialLineEdit.text()), 'subject': int(self.ui.subjectLineEdit.text()),
                  'loc_1': self.locations[self.ui.location1ComboBox.currentIndex()],
                  'loc_2': self.locations[self.ui.location2ComboBox.currentIndex()],
                  'obj': self.obj_idxs[self.ui.objectComboBox.currentIndex()],
                  'trial': int(self.ui.subjectTrialLineEdit.text())}
        return values


class ScorerMainWindow(QtWidgets.QMainWindow):
    key_action = QtCore.pyqtSignal(str, name="ScorerMainWindow.key_action")
    comments_received = QtCore.pyqtSignal(str, name='ScorerMainWindow.comments_received')

    def __init__(self):
        # noinspection PyUnresolvedReferences
        flags_ = QtCore.Qt.WindowFlags()
        super(ScorerMainWindow, self).__init__(flags=flags_)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setMenuBar(self.ui.menubar)
        self.session_file = None
        self._device = None
        self.ui.actionQuit.triggered.connect(self.close_all)
        self.ui.actionOpen_Camera.triggered.connect(self.get_camera_id_to_open)
        self.ui.actionOpen_Live_Session.triggered.connect(self.get_live_session_file_to_open)
        self.ui.actionOpen_Video_Session.triggered.connect(self.get_video_session_file_to_open)
        # self.ui.actionSave_to.triggered.connect(self.get_save_video_file)
        # self.ui.actionSave_to.setEnabled(False)
        self.ui.rawVideoCheckBox.setEnabled(False)
        self.ui.displayTsCheckBox.setChecked(True)
        self.setWindowTitle("Object in place task")
        self.comments_dialog = None

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
            self.ui.rotateComboBox.setEnabled(True)
            self.ui.rotateComboBox.currentIndexChanged.connect(self.device.set_rotate)
            self.device.can_acquire_signal.connect(self.change_acquisition_state)
            self.change_acquisition_state(dev.can_acquire)
            self.device.is_acquiring_signal.connect(self.acquisition_started_stopped)
            self.device.is_paused_signal.connect(self.has_paused)
            self.ui.playButton.clicked.connect(self.device.start_acquisition)
            self.ui.pauseButton.clicked.connect(self.device.set_paused)
            self.ui.stopButton.clicked.connect(self.device.stop_acquisition)
            self.ui.rawVideoCheckBox.toggled.connect(self.device.set_raw_out)
            self.ui.rawVideoCheckBox.setChecked(self.device.save_raw_video)
            self.ui.rawVideoCheckBox.setEnabled(True)
            self.ui.displayTsCheckBox.toggled.connect(self.device.set_display_time)
            self.device.size_changed_signal.connect(self.video_size_changed)
            self.device.session_set_signal.connect(self.session_was_set)
            self.device.video_file_changed_signal.connect(self.ui.destLabel.setText)
            self.device.trial_number_changed_signal.connect(self.ui.trialLabel.setText)
            self.ui.commentsButton.clicked.connect(self.get_comments)
            # noinspection PyUnresolvedReferences
            self.comments_received.connect(self.device.set_comments)
            self.device.yes_no_question_signal.connect(self.yes_no_question)
            # noinspection PyUnresolvedReferences
            self.yes_no_answer_signal.connect(self.device.yes_no_answer)
            self.device.error_signal.connect(self.error_and_close)
        self.ui.cameraWidget.set_device(self.device)

    @QtCore.pyqtSlot(bool)
    def session_was_set(self, s):
        if s:
            self.ui.actionOpen_Camera.setEnabled(False)
            self.ui.actionOpen_File.setEnabled(False)
            self.ui.actionOpen_Video_Session.setEnabled(False)
            self.ui.actionOpen_Live_Session.setEnabled(False)
        else:
            error = QtWidgets.QErrorMessage()
            error.showMessage("Error in setting session. Not set.")
            self.session_file = None

    @QtCore.pyqtSlot()
    def video_size_changed(self):
        self.updateGeometry()

    @QtCore.pyqtSlot()
    def video_finished(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)

        msg.setText("Video Completed")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        msg.exec_()

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
            self.ui.scaleComboBox.setEnabled(False)
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

    @QtCore.pyqtSlot(str)
    def error_and_close(self, e):
        error = QtWidgets.QErrorMessage()
        error.showMessage(e)
        error.exec_()
        self.close_all()

    yes_no_answer_signal = QtCore.pyqtSignal(bool, name='ScorerWindow.yes_no_answer_signal')

    @QtCore.pyqtSlot(str)
    def yes_no_question(self, q):
        reply = QtWidgets.QMessageBox.question(self, 'Question', q, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        self.yes_no_answer_signal.emit(reply == QtWidgets.QMessageBox.Yes)

    @QtCore.pyqtSlot()
    def close_all(self):
        import sys
        if self.device:
            self.device.cleanup()
        sys.exit()

    @QtCore.pyqtSlot()
    def get_camera_id_to_open(self):
        # n_cameras = find_how_many_cameras()
        n_cameras = 5
        print("n_cameras = ", n_cameras)
        ops = [str(i) for i in range(n_cameras)]
        print("ops: ", ops)
        import time
        time.sleep(1)

        if len(ops) == 1:
            cam = ops[0]
        else:
            print("before dialog")
            # noinspection PyCallByClass,PyTypeChecker,PyArgumentList
            dialog_out = QtWidgets.QInputDialog.getItem(self, "Open Camera", "Which camera id do you want to open?",
                                                        ops)
            print("after dialog")
            if not dialog_out[1]:
                return
            cam = int(dialog_out[0])

        self.set_camera(cam)

    # noinspection PyArgumentList
    @QtCore.pyqtSlot()
    def get_video_file_to_open(self):
        import os

        # noinspection PyCallByClass,PyTypeChecker
        dialog_out = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video File",
                                                           os.getcwd(), "Videos (*.mp4 *.avi)")
        open_video_file = dialog_out[0]
        if open_video_file:
            self.set_video_in(open_video_file)

    # noinspection PyArgumentList
    @QtCore.pyqtSlot()
    def get_live_session_file_to_open(self):
        import os
        # noinspection PyCallByClass,PyTypeChecker
        dialog_out = QtWidgets.QFileDialog.getOpenFileName(self, "Open Live Session File",
                                                           os.getcwd(), "CSV (*.csv)")
        self.session_file = dialog_out[0]
        if self._device and isinstance(self._device, CameraDeviceManager):
            self._device.set_session(self.session_file)
        else:
            self.get_camera_id_to_open()

    # noinspection PyMethodMayBeStatic
    def get_video_session_file_to_open(self):
        import os
        # error = QtWidgets.QErrorMessage()
        # error.showMessage("Session processing from video not implemented yet.")
        # error.exec_()
        dialog_out = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video Session File",
                                                           os.getcwd(), "CSV (*.csv)")
        video_in_filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video Session File",
                                                                  os.getcwd(), "Videos (*.mp4 *.avi)")
        video_in_filename = video_in_filename[0]
        self.session_file = dialog_out[0]
        self.set_video_in(video_in_filename)
        if self._device and isinstance(self._device, VideoDeviceManager):
            self._device.set_session(self.session_file)
        else:
            raise RuntimeError("can't open video session ")

    # # noinspection PyArgumentList
    # @QtCore.pyqtSlot()
    # def get_save_video_file(self):
    #     import os
    #     # noinspection PyCallByClass,PyTypeChecker
    #     dialog_out = QtWidgets.QFileDialog.getSaveFileName(self, "Save Video File",
    #                                                        os.path.join(os.getcwd(), 'untitled.avi'),
    #                                                        "Videos (*.avi)")
    #     save_video_file = dialog_out[0]
    #     if save_video_file:
    #         self.device.set_out_video_file(save_video_file)
    #         self.ui.destLabel.setText(os.path.basename(save_video_file))
    #         self.ui.rawVideoCheckBox.setEnabled(False)

    def set_camera(self, camera_id):
        print("in set camera")
        if self.device:
            self.device.cleanup()
        self.device = CameraDeviceManager(camera_id=camera_id, session_file=self.session_file)
        self.ui.sourceLabel.setText("Camera: " + str(camera_id))
        self.ui.videoInSlider.setEnabled(False)
        self.ui.actionSave_to.setEnabled(True)
        self.ui.scaleComboBox.addItems(self.device.scales_possible)
        self.ui.scaleComboBox.setCurrentIndex(self.device.scale_init)
        self.ui.scaleComboBox.setEnabled(True)
        self.ui.scaleComboBox.currentIndexChanged.connect(self.device.change_scale)
        self.ui.rotateComboBox.addItems([str(i) for i in self.device.rotate_options])
        self.ui.rotateComboBox.setEnabled(True)
        self.ui.rotateComboBox.setCurrentIndex(0)
        self.ui.rotateComboBox.currentIndexChanged.connect(self.device.set_rotate)

    def set_video_in(self, video_filename):
        import os
        if self.device:
            self.device.cleanup()
        self.device = VideoDeviceManager(video_file=video_filename, session_file=self.session_file)
        self.ui.sourceLabel.setText("File: " + os.path.basename(video_filename))
        last_frame = self.device.video_last_frame()
        self.ui.videoInSlider.setEnabled(True)
        self.ui.videoInSlider.setMinimum(0)
        self.ui.videoInSlider.setMaximum(last_frame)
        self.ui.actionSave_to.setEnabled(True)
        self.ui.scaleComboBox.setEnabled(False)
        self.device.video_finished_signal.connect(self.video_finished)
        self.device.frame_pos_signal.connect(self.ui.videoInSlider.setValue)
        self.ui.videoInSlider.sliderMoved.connect(self.device.skip_to_frame)

    def keyPressEvent(self, event):
        if self.device:
            if not event.isAutoRepeat() and event.key() in self.device.dir_keys:
                msg = DeviceManager.dir_keys[event.key()] + '1'
                self.key_action.emit(msg)
        event.accept()

    def keyReleaseEvent(self, event):
        if self.device:
            if not event.isAutoRepeat() and event.key() in self.device.dir_keys:
                msg = DeviceManager.dir_keys[event.key()] + '0'
                self.key_action.emit(msg)
        event.accept()

    @QtCore.pyqtSlot()
    def get_comments(self):
        # noinspection PyArgumentList
        dialog = QtWidgets.QInputDialog(None)
        dialog.setInputMode(QtWidgets.QInputDialog.TextInput)
        dialog.setLabelText("Comments:")
        dialog.setWindowTitle("Insert Comments")
        dialog.setOption(QtWidgets.QInputDialog.UsePlainTextEditForTextInput)
        # noinspection PyUnresolvedReferences
        dialog.accepted.connect(self.process_comments)
        self.comments_dialog = dialog
        dialog.show()

    def process_comments(self):
        text = self.comments_dialog.textValue()
        print("window comments: " + text)
        self.comments_received.emit(text)


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
