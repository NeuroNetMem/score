import cv2
from PyQt4 import QtGui, QtCore


class Capture:
    def __init__(self):
        self.capturing = False
        self.c = cv2.VideoCapture(0)

    def start_capture(self):
        print("pressed start")
        self.capturing = True
        cap = self.c
        while self.capturing:
            ret, frame = cap.read()
            cv2.imshow("Capture", frame)
            cv2.waitKey(5)
        cv2.destroyAllWindows()

    def end_capture(self):
        print("pressed End")
        self.capturing = False

    def quit_capture(self):
        print("pressed Quit")
        cap = self.c
        cv2.destroyAllWindows()
        cap.release()
        QtCore.QCoreApplication.quit()


class Window(QtGui.QWidget):
    def __init__(self):

        QtGui.QWidget.__init__(self)
        self.setWindowTitle('Control Panel')

        self.capture = Capture()
        self.start_button = QtGui.QPushButton('Start', self)
        self.start_button.clicked.connect(self.capture.start_capture)

        self.end_button = QtGui.QPushButton('End', self)
        self.end_button.clicked.connect(self.capture.end_capture)

        self.quit_button = QtGui.QPushButton('Quit', self)
        self.quit_button.clicked.connect(self.capture.quit_capture)

        vbox = QtGui.QVBoxLayout(self)
        vbox.addWidget(self.start_button)
        vbox.addWidget(self.end_button)
        vbox.addWidget(self.quit_button)

        self.setLayout(vbox)
        self.setGeometry(100, 100, 200, 200)
        self.show()


if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    window = Window()
    sys.exit(app.exec_())
