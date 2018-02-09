# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'video_control_ui.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_VideoControlWidget(object):
    def setupUi(self, VideoControlWidget):
        VideoControlWidget.setObjectName("VideoControlWidget")
        VideoControlWidget.resize(336, 214)
        VideoControlWidget.setMinimumSize(QtCore.QSize(336, 0))
        VideoControlWidget.setMaximumSize(QtCore.QSize(336, 16777215))
        self.verticalLayout = QtWidgets.QVBoxLayout(VideoControlWidget)
        self.verticalLayout.setContentsMargins(-1, -1, -1, 6)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(VideoControlWidget)
        self.groupBox.setToolTipDuration(34)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setContentsMargins(-1, -1, -1, 4)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox_2 = QtWidgets.QGroupBox(self.groupBox)
        self.groupBox_2.setMinimumSize(QtCore.QSize(0, 56))
        self.groupBox_2.setMaximumSize(QtCore.QSize(140, 56))
        self.groupBox_2.setObjectName("groupBox_2")
        self.rewindButton = QtWidgets.QToolButton(self.groupBox_2)
        self.rewindButton.setGeometry(QtCore.QRect(10, 20, 31, 31))
        self.rewindButton.setMaximumSize(QtCore.QSize(32, 32))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/newPrefix/resources/icons/icons8-rewind-50.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.rewindButton.setIcon(icon)
        self.rewindButton.setIconSize(QtCore.QSize(24, 24))
        self.rewindButton.setObjectName("rewindButton")
        self.pauseButton_2 = QtWidgets.QToolButton(self.groupBox_2)
        self.pauseButton_2.setGeometry(QtCore.QRect(40, 20, 31, 31))
        self.pauseButton_2.setMaximumSize(QtCore.QSize(32, 32))
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/newPrefix/resources/icons/icons8-pause-button-50.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.pauseButton_2.setIcon(icon1)
        self.pauseButton_2.setIconSize(QtCore.QSize(24, 24))
        self.pauseButton_2.setObjectName("pauseButton_2")
        self.playButton = QtWidgets.QToolButton(self.groupBox_2)
        self.playButton.setGeometry(QtCore.QRect(70, 20, 31, 31))
        self.playButton.setMaximumSize(QtCore.QSize(32, 32))
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/newPrefix/resources/icons/icons8-play-50.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.playButton.setIcon(icon2)
        self.playButton.setIconSize(QtCore.QSize(24, 24))
        self.playButton.setCheckable(False)
        self.playButton.setObjectName("playButton")
        self.fastForwardButton = QtWidgets.QToolButton(self.groupBox_2)
        self.fastForwardButton.setGeometry(QtCore.QRect(100, 20, 31, 31))
        self.fastForwardButton.setMaximumSize(QtCore.QSize(32, 32))
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/newPrefix/resources/icons/icons8-fast-forward-50.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.fastForwardButton.setIcon(icon3)
        self.fastForwardButton.setIconSize(QtCore.QSize(24, 24))
        self.fastForwardButton.setObjectName("fastForwardButton")
        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)
        self.groupBox_4 = QtWidgets.QGroupBox(self.groupBox)
        self.groupBox_4.setMinimumSize(QtCore.QSize(0, 56))
        self.groupBox_4.setMaximumSize(QtCore.QSize(16777215, 56))
        self.groupBox_4.setObjectName("groupBox_4")
        self.gridLayout.addWidget(self.groupBox_4, 2, 0, 1, 1)
        self.horizontalSlider = QtWidgets.QSlider(self.groupBox)
        self.horizontalSlider.setAccessibleName("")
        self.horizontalSlider.setAutoFillBackground(True)
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.horizontalSlider.setTickInterval(10)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.gridLayout.addWidget(self.horizontalSlider, 3, 0, 1, 2)
        self.groupBox_3 = QtWidgets.QGroupBox(self.groupBox)
        self.groupBox_3.setMinimumSize(QtCore.QSize(0, 56))
        self.groupBox_3.setMaximumSize(QtCore.QSize(90, 56))
        self.groupBox_3.setObjectName("groupBox_3")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox_3)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.speedComboBox = QtWidgets.QComboBox(self.groupBox_3)
        self.speedComboBox.setMaximumSize(QtCore.QSize(60, 16777215))
        self.speedComboBox.setObjectName("speedComboBox")
        self.verticalLayout_2.addWidget(self.speedComboBox)
        self.gridLayout.addWidget(self.groupBox_3, 1, 1, 1, 1)
        self.groupBox_5 = QtWidgets.QGroupBox(self.groupBox)
        self.groupBox_5.setObjectName("groupBox_5")
        self.gridLayout.addWidget(self.groupBox_5, 2, 1, 1, 1)
        self.verticalLayout.addWidget(self.groupBox)
        self.line = QtWidgets.QFrame(VideoControlWidget)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout.addWidget(self.line)

        self.retranslateUi(VideoControlWidget)
        QtCore.QMetaObject.connectSlotsByName(VideoControlWidget)

    def retranslateUi(self, VideoControlWidget):
        _translate = QtCore.QCoreApplication.translate
        VideoControlWidget.setWindowTitle(_translate("VideoControlWidget", "Form"))
        self.groupBox.setTitle(_translate("VideoControlWidget", "Video in controls"))
        self.groupBox_2.setTitle(_translate("VideoControlWidget", "Video play"))
        self.rewindButton.setText(_translate("VideoControlWidget", "..."))
        self.pauseButton_2.setText(_translate("VideoControlWidget", "..."))
        self.playButton.setText(_translate("VideoControlWidget", "..."))
        self.fastForwardButton.setText(_translate("VideoControlWidget", "..."))
        self.groupBox_4.setTitle(_translate("VideoControlWidget", "Time in video"))
        self.groupBox_3.setTitle(_translate("VideoControlWidget", "Playback speed"))
        self.groupBox_5.setTitle(_translate("VideoControlWidget", "GroupBox"))

import score_behavior.video_in_icons_rc
