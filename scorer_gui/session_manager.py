import numpy as np
import pandas as pd
from pandas.core.common import PandasError


class SessionManager:
    required_columns = ('condition', 'goal', 'group', 'session', 'rat', 'trial', 'originalnr')

    def __init__(self, filename, initial_trial=1, extra_event_columns=None, extra_trial_columns=None):
        self.scheme_file = filename
        try:
            self.scheme = pd.DataFrame.from_csv(self.scheme_file, index_col='run_nr')
        except PandasError:
            raise ValueError("couldn't open file correctly")
        if not set(self.scheme.columns) > set(self.required_columns):
            raise ValueError('required columns were not present')
        self.cur_trial = 1
        self.cur_run = initial_trial
        self.trial_ongoing = False
        self.trial_ready = False

        self.result_columns = None
        self.result_file = None
        self.trials = None

        self.log_file = None
        self.event_columns = None
        self.events = None

        self.comments = ''
        if not extra_event_columns:
            extra_event_columns = []
        self.extra_event_columns = extra_event_columns

        if not extra_trial_columns:
            extra_trial_columns = []
        self.extra_trial_columns = extra_trial_columns

        self.open_result_file()
        self.open_log_file()

    def open_result_file(self):
        import os
        import shutil
        self.result_file = self.get_result_file_name()
        self.result_columns = list(self.required_columns)
        self.result_columns.insert(0, 'run_nr')
        self.result_columns.extend(('start_date', 'loc_1_time', 'loc_2_time', 'total', 'trial_nr', 'comments'))
        self.result_columns.extend(self.extra_trial_columns)
        if os.path.exists(self.result_file):
            shutil.copyfile(self.result_file, self.result_file + '.bk')
            self.trials = pd.DataFrame.from_csv(self.result_file, index_col='trial_nr')
            self.cur_trial = self.trials.index.max() + 1
        else:
            self.trials = pd.DataFrame(columns=self.result_columns)
            self.trials.set_index('trial_nr', inplace=True)

    def get_result_file_name(self):
        import os
        dirname = os.path.dirname(self.scheme_file)
        basename, _ = os.path.splitext(os.path.basename(self.scheme_file))
        filename = os.path.join(dirname, basename + '_results.csv')
        return filename

    def open_log_file(self):
        import os
        import shutil

        self.log_file = self.get_log_file_name()
        self.event_columns = ['wall_time', 'trial_time', 'frame', 'type', 'start_stop']
        self.event_columns.extend(self.extra_event_columns)
        if os.path.exists(self.log_file):
            shutil.copyfile(self.log_file, self.log_file + '.bk')
            self.events = pd.DataFrame.from_csv(self.log_file, index_col='wall_time')
        else:
            self.events = pd.DataFrame(columns=self.event_columns)
            self.events.set_index('wall_time', inplace=True)

    def get_log_file_name(self):
        import os
        dirname = os.path.dirname(self.scheme_file)
        basename, _ = os.path.splitext(os.path.basename(self.scheme_file))
        filename = os.path.join(dirname, basename + '_log.csv')
        return filename

    def get_scheme_trial_info(self):
        try:
            s = self.scheme.ix[self.cur_run].copy()
            s['trial_nr'] = self.cur_trial
            s['run_nr'] = self.cur_run
        except KeyError:
            raise ValueError("trial not present")
        return s

    def get_trial_info(self):
        s = self.trials.ix[self.cur_trial]
        s['trial_nr'] = self.cur_trial
        return s

    def set_trial_info(self, info):
        import datetime
        info['start_date'] = str(datetime.datetime.now())[:-4]
        df_update = pd.DataFrame.from_dict(info, orient='index')
        df_update = df_update.transpose()
        print('finishing setting trial up')

        df_update.set_index('trial_nr', inplace=True)
        self.trials.loc[info['trial_nr']] = np.NaN
        self.trials.update(df_update)

    def set_trial_finished(self):
        self.cur_trial += 1
        self.trial_ongoing = False
        self.trials.to_csv(self.result_file)
        self.events.to_csv(self.log_file)

    def set_trial_number(self, i):
        self.cur_run = i

    def get_video_file_name_for_trial(self):
        import os
        dirname = os.path.dirname(self.scheme_file)
        basename, _ = os.path.splitext(os.path.basename(self.scheme_file))
        trial_no_str = str(self.cur_trial).zfill(4)
        filename = os.path.join(dirname, basename + '_t' + trial_no_str + '.avi')
        return filename

    def set_event(self, ts, frame_no, msg, *extra_data):
        import time
        start_stop = bool(int(msg[-1]))
        msg = msg[:-1]
        row = [ts, frame_no, msg, start_stop]
        row.extend(extra_data)
        self.events.loc[time.time()] = row

    def add_trial(self):
        self.cur_trial += 1

    def skip_trial(self):
        self.cur_run += 1

    def close(self):
        self.events.to_csv(self.log_file)
        self.trials.to_csv(self.result_file)


class VideoSessionManager(SessionManager):
    pass


class LiveSessionManager(SessionManager):
    pass

