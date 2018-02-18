import numpy as np
import pandas as pd
from pandas.core.common import PandasError


import datetime
import logging
import os.path

logger = logging.getLogger(__name__)


class SessionManager:
    required_columns = ('condition', 'group', 'session', 'subject', 'trial',)

    def __init__(self, filename, initial_trial=1, extra_event_columns=None, extra_trial_columns=None,
                 min_free_disk_space=0, mode='live', r_keys=None):

        import platform
        free_disk_space = 400
        logger.info("Creating session manager from file {} starting from trial {}".format(filename, initial_trial))
        if platform.system() == 'Darwin' or platform.system() == 'Linux':
            import os
            st = os.statvfs(filename)
            free_disk_space = int(st.f_frsize * st.f_bfree / 1.e9)
        elif platform.system() == 'Windows':
            import os
            import ctypes
            dirname = os.path.dirname(os.path.abspath(filename))
            free_bytes = ctypes.c_ulonglong(0)
            _ = ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(dirname), None, None,
                                                           ctypes.pointer(free_bytes))
            free_disk_space = free_bytes.value / 1024 / 1024 / 1024
        print("{} GB of disk space available".format(free_disk_space))
        logger.info("{} GB of disk space available".format(free_disk_space))
        if min_free_disk_space > 0 and free_disk_space < min_free_disk_space:
            logger.error("""Insufficient amount of free disk space, (min {} GB needed).
This program will cowardly refuse to continue""".format(min_free_disk_space))
            raise RuntimeError("""Insufficient amount of free disk space, (min {} GB needed).
This program will cowardly refuse to continue""".format(min_free_disk_space))
        self.mode = mode
        self.scheme_file = filename
        self.cur_trial = 1
        try:
            self.scheme = pd.DataFrame.from_csv(self.scheme_file, index_col='run_nr')
        except PandasError:
            raise ValueError("couldn't open file correctly")
        if not set(self.scheme.columns) > set(self.required_columns):
            raise ValueError('required columns were not present')
        self.cur_run = initial_trial
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

        if r_keys:
            self.r_keys = r_keys
        else:
            self.r_keys = []

    def open_result_file(self):
        import os
        import shutil
        self.result_file = self.get_result_file_name()
        self.result_columns = list(self.required_columns)
        self.result_columns.insert(0, 'run_nr')
        self.result_columns.extend(('start_date', 'loc_1_time', 'loc_2_time',
                                    'loc_1_time_5', 'loc_2_time_5',
                                    'total', 'sequence_nr', 'comments', 'originalnr', 'goal', 'video_out_filename',
                                    'video_out_raw_filename'))
        self.result_columns.extend(self.extra_trial_columns)
        logger.info("Attempting to open result file {}".format(self.result_file))
        if os.path.exists(self.result_file):
            logger.info("File exists, backing it up")
            shutil.copyfile(self.result_file, self.result_file + '.bk')
            self.trials_results = pd.DataFrame.from_csv(self.result_file, index_col='sequence_nr')
            self.cur_trial = self.trials_results.index.max() + 1
        else:
            self.trials_results = pd.DataFrame(columns=self.result_columns)
            self.trials_results.set_index('sequence_nr', inplace=True)
        logger.debug("File ready for writing")

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
        logger.info("Attempting to open session log file {}".format(self.log_file))
        if os.path.exists(self.log_file):
            logger.info("File exists, backing it up")
            shutil.copyfile(self.log_file, self.log_file + '.bk')
            self.events = pd.DataFrame.from_csv(self.log_file, index_col='wall_time')
        else:
            self.events = pd.DataFrame(columns=self.event_columns)
            self.events.set_index('wall_time', inplace=True)
        logger.debug("File ready for writing")

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
        logger.log(5, "Getting trial {}", self.cur_trial)
        return s

    def set_trial_info(self, info):
        import datetime
        info['start_date'] = str(datetime.datetime.now())[:-4]
        df_update = pd.DataFrame.from_dict(info, orient='index')
        df_update = df_update.transpose()
        logger.info("updating trial {}".format(info['sequence_nr']))
        logger.info("update info: {}".format(str(info)))
        assert info['sequence_nr'] == self.cur_trial

        df_update.set_index('sequence_nr', inplace=True)
        self.trials_results.loc[info['sequence_nr']] = np.NaN
        self.trials_results.update(df_update)

        # complete the results dataframe with info from the scheme dataframe
        r = self.trials_results.loc[info['sequence_nr']].copy()
        r.update(self.scheme.loc[self.cur_run])
        self.trials_results.loc[info['sequence_nr']] = r

    def set_trial_finished(self, video_out_filename, video_out_raw_filename):
        if self.comments:
            self.trials_results.loc[self.cur_trial]['comments'] = self.comments
        self.trials_results.loc[self.cur_trial]['video_out_filename'] = os.path.basename(video_out_filename)
        self.trials_results.loc[self.cur_trial]['video_out_raw_filename'] = os.path.basename(video_out_raw_filename)
        self.trials_results.to_csv(self.result_file)
        self.events.to_csv(self.log_file)
        logger.info("finalized trial {}".format(self.cur_trial))
        self.cur_trial += 1
        self.cur_run += 1

    def set_trial_number(self, i):
        self.cur_run = i

    def set_comments(self, comments):
        self.comments = comments

    @staticmethod
    def make_datetime_string(d):
        a = '{:0>4}-{:0>2}-{:0>2}_{:0>2}.{:0>2}.{:0>2}'.format(d.year, d.month, d.day, d.hour, d.minute, d.second)
        return a

    @staticmethod
    def make_raw_filename(video_filename):
        import os
        dirname = os.path.dirname(video_filename)
        basename, _ = os.path.splitext(os.path.basename(video_filename))
        filename = os.path.join(dirname, basename + '_raw.avi')
        return filename

    def get_video_out_file_name_for_trial(self):
        import os
        dirname = os.path.dirname(self.scheme_file)
        basename, _ = os.path.splitext(os.path.basename(self.scheme_file))
        trial_no_str = str(self.cur_trial).zfill(4)
        codes = {'live': 'L', 'video': 'V'}
        mode_code = codes[self.mode]
        date_string = self.make_datetime_string(datetime.datetime.now())
        filename = os.path.join(dirname, basename + '_t' + trial_no_str + mode_code + date_string + '.avi')
        filename_raw = self.make_raw_filename(filename)
        logger.info("Saving video to file {}".format(filename))
        return filename, filename_raw

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
        logger.info("Analyzing trial {}".format(self.cur_trial))
        loc_1 = info['loc_1']
        loc_2 = info['loc_2']

        st = lt.iloc[0]['trial_time']
        en = st + 300
        trial_5_min = nts.IntervalSet(st, en, time_units='s')
        r_keys = self.r_keys
        locations = r_keys
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
        logger.info("Closed csv files")
