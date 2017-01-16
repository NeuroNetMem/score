import numpy as np
import pandas as pd

class SessionManager:
    def __init__(self, filename, initial_trial = 0):
        # raises ValueError
        pass

    def get_scheme_trial_info(self):
        # raises ValueError
        pass

    def set_trial_info(self, info):
        # raises ValueError
        pass

    def get_video_file_name_for_trial(self):
        pass

    def set_event(self, ts, frame_no, msg):
        pass


class VideoSessionManager(SessionManager):
    pass


class LiveSessionManager(SessionManager):
    pass
