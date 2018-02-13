from PyQt5 import QtCore
from PyQt5 import QtWidgets


class SessionController(QtCore.QObject):
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