

from PyQt5 import QtCore
from PyQt5 import QtWidgets

import logging
import os
import sys

from score_behavior import GIT_VERSION
# noinspection PyUnresolvedReferences
from score_behavior.score_controller import VideoDeviceManager, CameraDeviceManager
from score_behavior.video_control import VideoControlWidget
from score_behavior.score_window_ui import Ui_MainWindow
from score_behavior.ObjectSpace.analyzer import ObjectSpaceFrameAnalyzer
from score_behavior.global_defs import DeviceState
from score_behavior.score_config import config_init, get_config_section


class ScorerMainWindow(QtWidgets.QMainWindow):
    key_action = QtCore.pyqtSignal(str, name="ScorerMainWindow.key_action")
    comments_received = QtCore.pyqtSignal(str, name='ScorerMainWindow.comments_received')

    def __init__(self):
        super(ScorerMainWindow, self).__init__(flags=QtCore.Qt.WindowFlags())
        self.do_track = True
        self.read_config()
        self.log = logging.getLogger(__name__)
        self.log.info('Initializing main window')

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setMenuBar(self.ui.menubar)
        self.session_file = None
        self._device = None
        self._analyzer = None
        self.ui.actionQuit.triggered.connect(self.close_all)
        self.ui.actionOpen_Camera.triggered.connect(self.get_camera_id_to_open)
        self.ui.actionOpen_Live_Session.triggered.connect(self.get_live_session_file_to_open)
        self.ui.actionOpen_Video_Session.triggered.connect(self.get_video_session_file_to_open)
        self.ui.actionStop_Acquisition.setEnabled(False)

        self.ui.rawVideoCheckBox.setEnabled(False)
        self.ui.displayTsCheckBox.setChecked(True)
        self.setWindowTitle("Object in place task")
        self.comments_dialog = None

    def read_config(self):
        d = get_config_section("general")
        if "do_track" in d:
            self.do_track = bool(d["do_track"])

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, dev):
        self._device = dev
        if dev:
            # noinspection PyUnresolvedReferences
            self.ui.cameraWidget.key_action.connect(self._analyzer.obj_state_change)
            self.ui.mirroredButton.setEnabled(True)
            self.ui.mirroredButton.toggled.connect(self.device.set_mirror)
            self.ui.rotateComboBox.setEnabled(True)
            self.ui.rotateComboBox.currentIndexChanged.connect(self.device.set_rotate)
            self.ui.playButton.clicked.connect(self.device.start_trial_acquisition)
            self.ui.pauseButton.clicked.connect(self.device.stop_trial_acquisition)
            self.ui.actionStop_Acquisition.triggered.connect(self.device.stop_acquisition)
            self.ui.rawVideoCheckBox.toggled.connect(self.device.set_raw_out)
            self.ui.rawVideoCheckBox.setChecked(self.device.save_raw_video)
            self.ui.rawVideoCheckBox.setEnabled(True)
            self.ui.displayTsCheckBox.toggled.connect(self.device.set_display_time)
            self.device.state_changed_signal.connect(self.change_device_state)
            self.change_device_state(dev.state)
            self._analyzer.device = self.device
            # self.device.can_acquire_signal.connect(self.change_acquisition_state)
            # self.change_acquisition_state(dev.can_acquire)
            # self.device.is_acquiring_signal.connect(self.acquisition_started_stopped)
            # self.device.is_paused_signal.connect(self.has_paused)
            self.device.size_changed_signal.connect(self.video_size_changed)
            self.device.video_out_file_changed_signal.connect(self.ui.destLabel.setText)
            self.device.trial_number_changed_signal.connect(self.ui.trialLabel.setText)
            self.device.error_signal.connect(self.error_and_close)
            self.device.yes_no_question_signal.connect(self.yes_no_question)

            # noinspection PyUnresolvedReferences
            self.yes_no_answer_signal.connect(self.device.yes_no_answer)

            if self.do_track:
                self._analyzer.init_tracker(self.device.frame_size)

            self.ui.cameraWidget.mouse_press_action_signal.connect(self._analyzer.mouse_press_action)
            self.ui.cameraWidget.mouse_move_action_signal.connect(self._analyzer.mouse_move_action)
            self.ui.cameraWidget.mouse_release_action_signal.connect(self._analyzer.mouse_release_action)
            self.ui.cameraWidget.key_action.connect(self._analyzer.obj_state_change)
            self.device.set_analyzer(self._analyzer)
            # noinspection PyUnresolvedReferences
            self.key_action.connect(self._analyzer.obj_state_change)

            if self._analyzer.tracker:
                self.ui.sidebarWidget.layout().addWidget(self._analyzer.tracker_controller.widget)
            self.setFocus()
            self.log.info('Setting device to {}'.format(dev))
        else:
            self.log.info("resetting acquisition device")

        self.ui.cameraWidget.set_device(self.device)

    @QtCore.pyqtSlot()
    def video_size_changed(self):
        (w, h) = self.device.display_frame_size
        self.log.debug('Video size changed to {}, {}'.format(w, h))
        self.updateGeometry()

    @QtCore.pyqtSlot()
    def video_finished(self):
        self.log.info('Video completed')
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)

        msg.setText("Video Completed")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        msg.exec_()

    @QtCore.pyqtSlot(DeviceState)
    def change_device_state(self, state):
        if state == DeviceState.NOT_READY:
            self.ui.playButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(False)
            self.ui.scaleComboBox.setEnabled(True)
            self.ui.rotateComboBox.setEnabled(True)
            self.ui.mirroredButton.setEnabled(True)
        elif state == DeviceState.READY:
            self.ui.playButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.actionStop_Acquisition.setEnabled(False)
            self.ui.scaleComboBox.setEnabled(False)
            self.ui.rotateComboBox.setEnabled(False)
            self.ui.mirroredButton.setEnabled(False)
        elif state == DeviceState.ACQUIRING:
            self.ui.playButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(True)
            self.ui.actionStop_Acquisition.setEnabled(True)
            self.ui.scaleComboBox.setEnabled(False)
            self.ui.rotateComboBox.setEnabled(False)
            self.ui.mirroredButton.setEnabled(False)

    @QtCore.pyqtSlot(str)
    def error_and_close(self, e):
        self.log.error('Closing due to: {}'.format(e))
        error = QtWidgets.QErrorMessage()
        error.showMessage(e)
        error.exec_()
        self.close_all()

    yes_no_answer_signal = QtCore.pyqtSignal(bool, name='ScorerWindow.yes_no_answer_signal')

    @QtCore.pyqtSlot(str)
    def yes_no_question(self, q):
        self.log.debug('Y/N question')
        reply = QtWidgets.QMessageBox.question(self, 'Question', q, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        self.yes_no_answer_signal.emit(reply == QtWidgets.QMessageBox.Yes)

    @QtCore.pyqtSlot()
    def close_all(self):
        self.log.debug('Closing all')
        if self.device:
            self.device.cleanup()
        if self._analyzer:
            self._analyzer.close()
        QtCore.QCoreApplication.quit()

    @QtCore.pyqtSlot()
    def get_camera_id_to_open(self):
        # n_cameras = find_how_many_cameras()
        n_cameras = 5
        self.log.debug("n_cameras: {}".format(n_cameras))
        ops = [str(i) for i in range(n_cameras)]
        import time
        time.sleep(1)

        if len(ops) == 1:
            cam = ops[0]
        else:
            # noinspection PyCallByClass,PyTypeChecker,PyArgumentList
            dialog_out = QtWidgets.QInputDialog.getItem(self, "Open Camera", "Which camera id do you want to open?",
                                                        ops)
            if not dialog_out[1]:
                return
            cam = int(dialog_out[0])
        self.log.debug('Chose camera {}'.format(cam))
        self.set_camera(cam)

    # noinspection PyArgumentList
    @QtCore.pyqtSlot()
    def get_video_file_to_open(self):
        self.log.debug('Asking for video location to open...')
        # noinspection PyCallByClass,PyTypeChecker
        dialog_out = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video File",
                                                           os.getcwd(), "Videos (*.mp4 *.avi)")
        open_video_file = dialog_out[0]
        if open_video_file:
            self.set_video_in(open_video_file)
        else:
            self.log.debug('No video file location given. Doing nothing.'.format(open_video_file))

    # noinspection PyArgumentList
    @QtCore.pyqtSlot()
    def get_live_session_file_to_open(self):
        self.log.debug('Asking for session file location to open...')
        # noinspection PyCallByClass,PyTypeChecker
        dialog_out = QtWidgets.QFileDialog.getOpenFileName(self, "Open Live Session File",
                                                           os.getcwd(), "CSV (*.csv)")
        session_file = dialog_out[0]
        if session_file:
            self.log.info('Session file opened: {}'.format(self.session_file))
            self.session_file = session_file

            if self._device and isinstance(self._device, CameraDeviceManager):
                self._device.set_session(self.session_file)
            else:
                self.get_camera_id_to_open()
        else:
            self.log.info('No session file given. Doing nothing.')

    # noinspection PyMethodMayBeStatic
    def get_video_session_file_to_open(self):

        self.log.debug("Setting video session ")

        dialog_out = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video Session File",
                                                           os.getcwd(), "CSV (*.csv)")
        video_in_filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video Session File",
                                                                  os.getcwd(), "Videos (*.mp4 *.avi)")
        video_in_filename = video_in_filename[0]
        self.session_file = dialog_out[0]
        self.set_video_in(video_in_filename)
        if self._device and isinstance(self._device, VideoDeviceManager):
            self._device.set_session(self.session_file)
            self.log.debug("Video session file set to {} with video file {}".format(self.session_file,
                                                                                    video_in_filename))
        else:
            raise RuntimeError("can't open video session ")

    def set_camera(self, camera_id):
        self.log.debug('Set camera to {}'.format(camera_id))
        if self.device:
            self.device.cleanup()
        self._analyzer = ObjectSpaceFrameAnalyzer(self.device, parent=self)
        self._analyzer.error_signal.connect(self.error_and_close)
        self.device = CameraDeviceManager(camera_id=camera_id, session_file=self.session_file,
                                          analyzer=self._analyzer)
        self.ui.sourceLabel.setText("Camera: " + str(camera_id))
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
        if self.device:
            self.device.cleanup()
        control_widget = VideoControlWidget()
        self._analyzer = ObjectSpaceFrameAnalyzer(self.device, parent=self)
        self._analyzer.error_signal.connect(self.error_and_close)
        self.device = VideoDeviceManager(video_file=video_filename, session_file=self.session_file,
                                         widget=control_widget, analyzer=self._analyzer)
        self.ui.sourceLabel.setText("File: " + os.path.basename(video_filename))

        last_frame = self.device.video_last_frame()
        control_widget.ui.playButton.clicked.connect(self.device.play_action)
        control_widget.ui.pauseButton.clicked.connect(self.device.pause_action)
        control_widget.ui.fastForwardButton.clicked.connect(self.device.fastforward_action)
        control_widget.ui.rewindButton.clicked.connect(self.device.rewind_action)

        control_widget.ui.timeSlider.setEnabled(True)
        control_widget.ui.timeSlider.setMinimum(0)
        control_widget.ui.timeSlider.setMaximum(last_frame)
        control_widget.ui.timeSlider.setTickInterval(int(last_frame/10))
        self.ui.actionSave_to.setEnabled(True)
        self.ui.scaleComboBox.setEnabled(False)
        self.device.video_finished_signal.connect(self.video_finished)

        self.device.frame_pos_signal.connect(control_widget.ui.timeSlider.setValue)
        self.device.frame_pos_signal.connect(control_widget.set_frame)
        self.device.time_pos_signal.connect(control_widget.ui.timeLabel.setText)

        control_widget.ui.timeSlider.sliderMoved.connect(self.device.skip_to_frame)

        # self.ui.rotateComboBox.addItems([str(i) for i in self.device.rotate_options])
        # self.ui.rotateComboBox.setEnabled(True)
        # self.ui.rotateComboBox.setCurrentIndex(0)
        # self.ui.rotateComboBox.currentIndexChanged.connect(self.device.set_rotate)

        control_widget.ui.speedComboBox.addItems([str(i) for i in self.device.speed_possible])
        control_widget.ui.speedComboBox.setEnabled(True)
        # default speed is 1
        ix1 = [i for i in range(len(self.device.speed_possible)) if self.device.speed_possible[i] == '1']
        control_widget.ui.speedComboBox.setCurrentIndex(ix1[0])
        control_widget.ui.speedComboBox.currentIndexChanged.connect(self.device.speed_action)

        self.ui.sidebarWidget.layout().addWidget(control_widget)
        self.setFocus()

    def keyPressEvent(self, event):
        self.log.log(5, "key pressed {}, isAutorepeat {}".format(event.key(), event.isAutoRepeat()))
        if self.device:
            keymap = self._analyzer.key_interface()
            if not event.isAutoRepeat() and event.key() in keymap:
                msg = keymap[event.key()] + '1'
                self.key_action.emit(msg)
        event.accept()

    def keyReleaseEvent(self, event):
        self.log.log(5, "key released {}, isAutorepeat {}".format(event.key(), event.isAutoRepeat()))
        if self.device:
            keymap = self._analyzer.key_interface()
            if not event.isAutoRepeat() and event.key() in keymap:
                msg = keymap[event.key()] + '0'
                self.key_action.emit(msg)
        event.accept()


def _main():

    config_init()  # TODO add option for a outside configuration file
    d = get_config_section("general")
    if d['debug']:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.info('Starting Score with git version {}'.format(GIT_VERSION))
    if d['debug']:
        logging.info("Running in debug mode")
    else:
        logging.info("Running in release mode")

    try:
        app = QtWidgets.QApplication(sys.argv)

        window = ScorerMainWindow()
        # window.device = CameraDevice(mirrored=True)
        window.show()
        app.quitOnLastWindowClosed = True
        # noinspection PyUnresolvedReferences
        app.lastWindowClosed.connect(window.close_all)
        logging.info("Starting app")
        app.exec_()
        logging.info('All done.')
    except Exception as e:
        logging.error("Uncaught exception: {}".format(str(e)))


if __name__ == '__main__':
    logging.basicConfig(filename='scorer_log.log', level=logging.DEBUG, filemode='w')
    _main()
