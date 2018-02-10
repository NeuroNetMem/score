from PyQt5 import QtWidgets
from PyQt5 import QtCore

from .tracker_control_ui import Ui_TrackerControl


class TrackerControlWidget(QtWidgets.QWidget):
    def __init__(self):
        flags_ = QtCore.Qt.WindowFlags()
        super(TrackerControlWidget, self).__init__(flags=flags_)
        self.ui = Ui_TrackerControl()
        self.ui.setupUi(self)
