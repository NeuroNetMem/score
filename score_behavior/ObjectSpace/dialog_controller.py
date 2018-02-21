from PyQt5 import QtCore

import logging

logger = logging.getLogger(__name__)


class TrialDialogController(QtCore.QObject):
    dialog_done_signal = QtCore.pyqtSignal(name="TrialDialogController.dialog_done_signal")

    def __init__(self, caller, locations, object_files=None, parent=None):
        super(TrialDialogController, self).__init__(parent)
        self.object_files = object_files
        self.caller = caller
        self.scheme = None
        self.locations = locations
        self.dialog = None
        self.ok = False

    def set_scheme(self, scheme):
        self.scheme = scheme
        if self.dialog:
            self.dialog.set_values(scheme)

    def get_values(self):
        return self.dialog.get_values()

    @QtCore.pyqtSlot()
    def start_dialog(self):
        from score_behavior.ObjectSpace.trial_dialog import TrialDialog
        self.dialog = TrialDialog(caller=self.caller, trial_params=self.scheme, locations=self.locations,
                                  object_files=self.object_files)
        self.dialog.set_readonly(True)
        self.ok = self.dialog.exec_()
        logger.debug("Dialog has finished")
        self.dialog_done_signal.emit()
        logger.debug("And signal emitted")

    def exit_status(self):
        return self.ok

    def set_readonly(self, i):
        self.dialog.set_readonly(i)
