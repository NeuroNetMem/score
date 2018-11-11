#!/usr/bin/env bash

source activate opencv_pyqt5

cd ..
pyuic5 -x score_window_ui.ui -o score_window_ui.py
pyuic5 -x ObjectSpace/trial_dialog_ui.ui -o ObjectSpace/trial_dialog_ui.py
pyrcc5 video_in_icons.qrc -o video_in_icons_rc.py
pyuic5 video_control_ui.ui -o video_control_ui.py
pyuic5 tracking_controller/tracker_control_ui.ui -o tracking_controller/tracker_control_ui.py
pyuic5 score_session_manager_control_ui.ui -o score_session_manager_control_ui.py
pyrcc5 resources/icons/logo.qrc -o logo_rc.py

sed -i'' 's/video_in_icons_rc/score_behavior.video_in_icons_rc/g' video_control_ui.py
sed -i'' 's/logo_rc/score_behavior.logo_rc/g' score_window_ui.py