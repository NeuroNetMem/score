# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'obj_scorer_ui.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(663, 541)
        MainWindow.setMinimumSize(QtCore.QSize(647, 500))
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.cameraWidget = CameraWidget(self.centralwidget)
        self.cameraWidget.setObjectName("cameraWidget")
        self.verticalLayout.addWidget(self.cameraWidget)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.groupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox.setMinimumSize(QtCore.QSize(323, 90))
        self.groupBox.setMaximumSize(QtCore.QSize(350, 90))
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.groupBox)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.playButton = QtWidgets.QPushButton(self.groupBox)
        self.playButton.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/images/play.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.playButton.setIcon(icon)
        self.playButton.setIconSize(QtCore.QSize(32, 32))
        self.playButton.setObjectName("playButton")
        self.horizontalLayout.addWidget(self.playButton)
        self.pauseButton = QtWidgets.QPushButton(self.groupBox)
        self.pauseButton.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/images/pause.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pauseButton.setIcon(icon1)
        self.pauseButton.setIconSize(QtCore.QSize(32, 32))
        self.pauseButton.setObjectName("pauseButton")
        self.horizontalLayout.addWidget(self.pauseButton)
        self.pauseButton_2 = QtWidgets.QPushButton(self.groupBox)
        self.pauseButton_2.setText("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/images/stop.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pauseButton_2.setIcon(icon2)
        self.pauseButton_2.setIconSize(QtCore.QSize(32, 32))
        self.pauseButton_2.setObjectName("pauseButton_2")
        self.horizontalLayout.addWidget(self.pauseButton_2)
        self.horizontalLayout_2.addWidget(self.groupBox)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setMaximumSize(QtCore.QSize(200, 16777215))
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.sourceLabel = QtWidgets.QLabel(self.centralwidget)
        self.sourceLabel.setMaximumSize(QtCore.QSize(200, 16777215))
        self.sourceLabel.setText("")
        self.sourceLabel.setObjectName("sourceLabel")
        self.verticalLayout_2.addWidget(self.sourceLabel)
        self.horizontalLayout_2.addLayout(self.verticalLayout_2)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        spacerItem = QtWidgets.QSpacerItem(20, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 663, 22))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionOpen_Camera = QtWidgets.QAction(MainWindow)
        self.actionOpen_Camera.setObjectName("actionOpen_Camera")
        self.actionOpen_File = QtWidgets.QAction(MainWindow)
        self.actionOpen_File.setObjectName("actionOpen_File")
        self.menuFile.addAction(self.actionOpen_Camera)
        self.menuFile.addAction(self.actionOpen_File)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.cameraWidget.setToolTip(_translate("MainWindow", "Video Viewer for Behavioral Tracking"))
        self.cameraWidget.setWhatsThis(_translate("MainWindow", "A Video Viewer for OpenCV based behavioral trackingusing PyQt."))
        self.groupBox.setTitle(_translate("MainWindow", "Play Controls"))
        self.playButton.setShortcut(_translate("MainWindow", "Ctrl+Right"))
        self.pauseButton.setShortcut(_translate("MainWindow", "Ctrl+Space, Meta+Space"))
        self.pauseButton_2.setShortcut(_translate("MainWindow", "Ctrl+Down, Meta+Down"))
        self.label.setText(_translate("MainWindow", "Playing from:"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.actionOpen_Camera.setText(_translate("MainWindow", "Open Camera..."))
        self.actionOpen_File.setText(_translate("MainWindow", "Open File..."))

from scorer_gui.gui_qt_thread import CameraWidget
import scorer_gui.play_rc

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

