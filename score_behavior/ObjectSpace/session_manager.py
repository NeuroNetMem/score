import numpy as np
import pandas as pd
from pandas.core.common import PandasError

from score_behavior.ObjectSpace.analyzer import ObjectSpaceFrameAnalyzer


class SessionManager:
    required_columns = ('condition', 'group', 'session', 'subject', 'trial',)

    def __init__(self, filename, initial_trial=1, extra_event_columns=None, extra_trial_columns=None,
                 min_free_disk_space=0):

        import platform
        free_disk_space = 400

        if platform.system() == 'Darwin' or platform.system() == 'Linux':
            import os
            st = os.statvfs(filename)
            free_disk_space = int(st.f_frsize * st.f_bfree / 1.e9)
            print("{} GB of disk space available".format(free_disk_space))
        elif platform.system() == 'Windows':
            import os
            import ctypes
            dirname = os.path.dirname(os.path.abspath(filename))
            free_bytes = ctypes.c_ulonglong(0)
            _ = ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(dirname), None, None,
                                                           ctypes.pointer(free_bytes))
            free_disk_space = free_bytes.value / 1024 / 1024 / 1024
        if min_free_disk_space > 0 and free_disk_space < min_free_disk_space:
            raise RuntimeError("""Insufficient amount of free disk space, (min {} GB needed).
This program will cowardly refuse to continue""".format(min_free_disk_space))
        self.scheme_file = filename
        self.cur_trial = 1
        try:
            self.scheme = pd.DataFrame.from_csv(self.scheme_file, index_col='run_nr')
        except PandasError:
            raise ValueError("couldn't open file correctly")
        if not set(self.scheme.columns) > set(self.required_columns):
            raise ValueError('required columns were not present')
        self.cur_run = initial_trial
        self.trial_ongoing = False
        self.trial_ready = False

        self.result_columns = None
        self.result_file = None
        self.trials_results = None

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
        self.result_columns.extend(('start_date', 'loc_1_time', 'loc_2_time',
                                    'loc_1_time_5', 'loc_2_time_5',
                                    'total', 'sequence_nr', 'comments', 'originalnr', 'goal'))
        self.result_columns.extend(self.extra_trial_columns)
        if os.path.exists(self.result_file):
            shutil.copyfile(self.result_file, self.result_file + '.bk')
            self.trials_results = pd.DataFrame.from_csv(self.result_file, index_col='sequence_nr')
            self.cur_trial = self.trials_results.index.max() + 1
        else:
            self.trials_results = pd.DataFrame(columns=self.result_columns)
            self.trials_results.set_index('sequence_nr', inplace=True)

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
        self.event_columns = ['wall_time', 'trial_time', 'frame', 'sequence_nr', 'type', 'start_stop']
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
            s['sequence_nr'] = self.cur_trial
            s['run_nr'] = self.cur_run

            print('get scheme, cur_trial: ', self.cur_trial)
        except KeyError:
            raise ValueError("trial not present")
        return s

    def get_trial_info(self):
        s = self.trials_results.ix[self.cur_trial].copy()
        s['sequence_nr'] = self.cur_trial
        print('get trial: ', self.cur_trial)
        return s

    def set_trial_info(self, info):
        import datetime
        info['start_date'] = str(datetime.datetime.now())[:-4]
        df_update = pd.DataFrame.from_dict(info, orient='index')
        df_update = df_update.transpose()
        print('set trial, info[''sequence_nr''', info['sequence_nr'])
        print('cur_trial', self.cur_trial)
        assert info['sequence_nr'] == self.cur_trial

        df_update.set_index('sequence_nr', inplace=True)
        self.trials_results.loc[info['sequence_nr']] = np.NaN
        self.trials_results.update(df_update)

        # complete the results dataframe with info from the scheme dataframe
        r = self.trials_results.loc[info['sequence_nr']].copy()
        r.update(self.scheme.loc[self.cur_run])
        self.trials_results.loc[info['sequence_nr']] = r

    def set_trial_finished(self):
        self.trial_ongoing = False
        if self.comments:
            self.trials_results.loc[self.cur_trial]['comments'] = self.comments
        self.trials_results.to_csv(self.result_file)
        self.events.to_csv(self.log_file)
        self.cur_trial += 1
        self.cur_run += 1

    def set_trial_number(self, i):
        self.cur_run = i

    def set_comments(self, comments):
        self.comments = comments

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
        row = [ts, frame_no, self.cur_trial, msg, start_stop]
        row.extend(extra_data)
        self.events.loc[time.time()] = row

    def get_events_for_trial(self, i=None):
        if i is None:
            i = self.cur_trial
        lt = self.events.loc[self.events['sequence_nr'] == float(i)]
        if not lt.empty:
            assert lt.iloc[0]['type'] == 'TR' and \
                lt.iloc[-1]['type'] == 'TR' and \
                lt.iloc[1:-1]['type'].all() != 'TR' and \
                lt.iloc[0]['start_stop'] and \
                not lt.iloc[-1]['start_stop']
        return lt

    def get_scheme_trial(self, i=None):
        if i is None:
            i = self.cur_run
        return self.scheme.loc[i]

    def update_results_with_extra_data(self, info):
        info['sequence_nr'] = self.cur_trial
        df_update = pd.DataFrame.from_dict(info, orient='index')
        df_update = df_update.transpose()
        df_update.set_index('sequence_nr', inplace=True)
        # self.trials_results.loc[info['sequence_nr']] = np.NaN
        self.trials_results.update(df_update)

    def analyze_trial(self):
        # noinspection PyUnresolvedReferences
        import neuroseries as nts
        lt = self.get_events_for_trial()
        info = self.get_scheme_trial_info()
        loc_1 = info['loc_1']
        loc_2 = info['loc_2']

        st = lt.iloc[0]['trial_time']
        en = st + 300
        trial_5_min = nts.IntervalSet(st, en, time_units='s')
        r_keys = ObjectSpaceFrameAnalyzer.rect_coord.keys()
        locations = list(r_keys)
        explore_time = {}
        explore_time_5 = {}
        for l in locations:
            st = lt.loc[(lt['type'] == l) & (lt['start_stop'])]['trial_time']
            en = lt.loc[(lt['type'] == l) & (~(lt['start_stop'] == True))]['trial_time']
            explore = nts.IntervalSet(st, en, time_units='s')
            explore_time[l] = explore.tot_length(time_units='s')
            explore_5 = trial_5_min.intersect(explore)
            explore_time_5[l] = explore_5.tot_length(time_units='s')

        extra_info = {'loc_1_time': explore_time[loc_1],
                      'loc_2_time': explore_time[loc_2],
                      'loc_1_time_5': explore_time_5[loc_1],
                      'loc_2_time_5': explore_time_5[loc_2]}

        self.update_results_with_extra_data(extra_info)

    def add_trial(self):
        self.cur_trial += 1

    def skip_sequence_number(self):
        self.cur_trial += 1
        res = self.trials_results
        res.reset_index(inplace=True)
        res.ix[len(res) - 1, 'sequence_nr'] = 4
        res.set_index('sequence_nr', inplace=True)

    def skip_trial(self):
        self.cur_run += 1

    def close(self):
        self.events.to_csv(self.log_file)
        self.trials_results.to_csv(self.result_file)


class VideoSessionManager(SessionManager):
    pass


class LiveSessionManager(SessionManager):
    pass
