#!/usr/bin/env bash

source activate opencv_pyqt5

cd ..
pyuic5 -x obj_scorer_ui.ui -o obj_scorer_ui.py
pyrcc5  resources/icons/play.qrc -o play_rc.py
sed -i '' "s/play_rc/scorer_gui.play_rc/g" obj_scorer_ui.py