from PyQt5 import QtCore

from .tracker_widget import TrackerControlWidget


class TrackerController(QtCore.QObject):
    def __init__(self, tracker=None, parent=None):
        super(TrackerController, self).__init__(parent)
        self._tracker = tracker
        self.tracker.tracker_controller = self

        self.widget = TrackerControlWidget()

        self.widget.ui.showThreshCheckBox.setChecked(self.tracker.show_thresholded)
        self.widget.ui.thresholdSpinBox.setValue(self.tracker.component_threshold)
        self.widget.ui.speedSpinBox.setValue(self.tracker.speed_threshold)
        self.widget.ui.animalsLabel.setText('0/{}'.format(self.tracker.max_num_animals))
        self.widget.ui.stateLabel.setText(self.tracker.state_labels[self.tracker.state])

        self.widget.ui.backgroundButton.clicked.connect(self.begin_set_background)
        self.widget.ui.initButton.clicked.connect(self.init_animals)
        self.widget.ui.initButton.setEnabled(False)
        self.widget.ui.resetButton.clicked.connect(self.reset_animals)
        self.widget.ui.resetButton.setEnabled(False)
        self.widget.ui.showThreshCheckBox.toggled.connect(self.show_thresh_changed)
        self.widget.ui.thresholdSpinBox.valueChanged.connect(self.set_tracker_threshold)
        self.widget.ui.speedSpinBox.valueChanged.connect(self.set_speed_threshold)


        # TODO set initial value for thresholds in widget

    @property
    def tracker(self):
        return self._tracker

    @tracker.setter
    def tracker(self, t):
        self._tracker = t
        self._tracker.controller = self

    @QtCore.pyqtSlot()
    def begin_set_background(self):
        self.tracker.grab_background()

    @QtCore.pyqtSlot()
    def init_animals(self):
        self.tracker.add_animal_auto()

    @QtCore.pyqtSlot()
    def reset_animals(self):
        self.tracker.delete_all_animals()

    @QtCore.pyqtSlot(bool)
    def show_thresh_changed(self, val):
        self.tracker.show_thresholded = val

    @QtCore.pyqtSlot(float)
    def set_tracker_threshold(self, val):
        self.tracker.component_threshold = val

    @QtCore.pyqtSlot(float)
    def set_speed_threshold(self, val):
        self.tracker.speed_threshold = val

    def set_tracker_state(self, val):
        self.widget.ui.stateLabel.setText(val)
        if val != 'Inactive':
            self.widget.ui.initButton.setEnabled(True)
        else:
            self.widget.ui.initButton.setEnabled(False)

    def set_tracked_animals_number(self, val):
        self.widget.ui.animalsLabel.setText('{}/{}'.format(val, self.tracker.max_num_animals))
        if val > 0:
            self.widget.ui.resetButton.setEnabled(True)
        else:
            self.widget.ui.resetButton.setEnabled(False)
