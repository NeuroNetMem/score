#!/usr/bin/env bash

source activate opencv_pyqt5

cd ..
pyuic5 -x score_window_ui.ui -o score_window_ui.py
# pyrcc5  resources/icons/play.qrc -o play_rc.py
pyuic5 -x trial_dialog_ui.ui -o trial_dialog_ui.py
pyrcc5 resources/objects/obj.qrc -o obj_rc.py

#sed -i '' "s/play_rc/scorer_gui.play_rc/g" obj_scorer_ui.py
#sed -i '' "s/play_rc/scorer_gui.play_rc/g" trial_dialog_ui.py
sed -i '' "s/obj_rc/score_behavior.obj_rc/g" score_window_ui.py
sed -i '' "s/obj_rc/score_behavior.obj_rc/g" trial_dialog_ui.py