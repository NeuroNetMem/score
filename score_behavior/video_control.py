from PyQt5 import QtWidgets
from PyQt5 import QtCore

from score_behavior.video_control_ui import Ui_VideoControlWidget


class VideoControlWidget(QtWidgets.QWidget):
    def __init__(self):
        # noinspection PyUnresolvedReferences
        flags_ = QtCore.Qt.WindowFlags()
        super(VideoControlWidget, self).__init__(flags=flags_)
        self.ui = Ui_VideoControlWidget()
        self.ui.setupUi(self)

    @QtCore.pyqtSlot(int)
    def set_frame(self, val):
        self.ui.frameLabel.setText(str(val))
