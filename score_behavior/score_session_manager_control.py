from PyQt5 import QtWidgets
from PyQt5 import QtCore

from score_behavior.score_session_manager_control_ui import Ui_Form


class SessionManagerControlWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        flags_ = QtCore.Qt.WindowFlags()
        super(SessionManagerControlWidget, self).__init__(flags=flags_, parent=parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
