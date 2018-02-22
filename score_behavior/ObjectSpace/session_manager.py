import numpy as np
import pandas as pd
from pandas.core.common import PandasError


import datetime
import logging
import os.path
import glob

from score_behavior.score_config import get_config_section

logger = logging.getLogger(__name__)


# indices:
# - cur_scheduled_run: the ordinal number of run as per experiment sheet. That is, the serial number of the trial
#   involving all animals as planned (in the sheets, by the index 'run_nr'
# - cur_actual_run: the ordinal number of run as performed. This may be different from the above if some runs are
#   skipped or added
# - trial: the per subject trial number, which here is only a run feature, and should not be used as an index


class SessionManager:
    required_columns = ('condition', 'group', 'session', 'subject', 'trial',)

    def __init__(self, filename, initial_trial=1, extra_event_columns=None, extra_trial_columns=None,
                 min_free_disk_space=0, mode='live', r_keys=None):
        self.video_in_source = None
        self.video_in_glob = None
        self.extra_event_columns = []
        self.extra_trial_columns = []
        self.object_dir = None
        self.read_config()

        # Determine if there is enough space to continue
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

        self.cur_actual_run = 1
        try:
            self.scheme = pd.DataFrame.from_csv(self.scheme_file, index_col='run_nr')
        except PandasError:
            raise ValueError("couldn't open file correctly")
        if not set(self.scheme.columns) > set(self.required_columns):
            raise ValueError('required columns were not present')

        if self.mode == 'video':
            self.test_video_in_files()

        self.object_files = {} # TODO to subclass
        self.test_object_images()

        self.cur_scheduled_run = initial_trial
        self.trial_ready = False

        self.result_columns = None
        self.result_file = None
        self.trials_results = None

        self.event_log_file = None
        self.event_log_columns = None
        self.event_log = None

        self.comments = ''

        if not extra_event_columns:
            extra_event_columns = []
        self.extra_event_columns.extend(extra_event_columns)

        if not extra_trial_columns:
            extra_trial_columns = []
        self.extra_trial_columns.extend(extra_trial_columns)

        self.open_result_file()
        self.open_log_file()

        if r_keys:
            self.r_keys = r_keys
        else:
            self.r_keys = []

    def get_object_files(self):  # TODO To subclass
        return self.object_files

    def test_object_images(self):  # TODO To subclass
        """test that all the object images are there before starting the session"""
        import imghdr
        obj_idxs = list(pd.unique(self.scheme['obj']))
        self.object_files = {}
        for obj_idx in obj_idxs:
            fname = os.path.join(self.object_dir, str(obj_idx) + '.JPG')
            if not os.path.exists(fname):
                raise RuntimeError("Object image file {} does not exist".format(fname))
            if imghdr.what(fname) != 'jpeg':
                raise RuntimeError("File {} is not a JPG image".format(fname))
            self.object_files[obj_idx] = fname

    def test_video_in_files(self):
        """test that all the video files are there before a video session """
        import warnings
        if self.video_in_source == "glob":
            scheduled_trials = pd.unique(self.scheme['run_nr'])
            for i in scheduled_trials:
                fn = self.get_video_in_file_name_for_trial(i)
                if not os.path.exists(fn):
                    warnings.warn("Video in file {} does not exist".format(fn))
                    logger.warning("Video in file {} does not exist".format(fn))


    def read_config(self):
        config_dict = get_config_section("data_manager")
        if "extra_trial_columns" in config_dict:
            self.extra_trial_columns = config_dict["extra_trial_columns"]
        if "extra_event_columns" in config_dict:
            self.extra_event_columns = config_dict["extra_event_columns"]
        if "video_in_source" in config_dict:
            self.video_in_source = config_dict["video_in_source"]
        if "video_in_glob" in config_dict:
            self.video_in_glob = config_dict["video_in_glob"]
        if "object_dir" in config_dict:
            self.object_dir = config_dict["object_dir"]

    def open_result_file(self):
        import os
        import shutil
        self.result_file = self.get_result_file_name()
        self.result_columns = list(self.required_columns)
        self.result_columns.insert(0, 'run_nr')
        self.result_columns.extend(('start_date', 'loc_1_time', 'loc_2_time',
                                    'loc_1_time_5', 'loc_2_time_5',
                                    'total', 'sequence_nr', 'comments',  'goal', 'video_out_filename',
                                    'video_out_raw_filename'))
        self.result_columns.extend(self.extra_trial_columns)
        logger.info("Attempting to open result file {}".format(self.result_file))
        if os.path.exists(self.result_file):
            logger.info("File exists, backing it up")
            shutil.copyfile(self.result_file, self.result_file + '.bk')
            self.trials_results = pd.DataFrame.from_csv(self.result_file, index_col='sequence_nr')
            self.cur_actual_run = self.trials_results.index.max() + 1
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

        self.event_log_file = self.get_log_file_name()
        self.event_log_columns = ['wall_time', 'trial_time', 'frame', 'sequence_nr', 'type', 'start_stop']
        self.event_log_columns.extend(self.extra_event_columns)
        logger.info("Attempting to open session log file {}".format(self.event_log_file))
        if os.path.exists(self.event_log_file):
            logger.info("File exists, backing it up")
            shutil.copyfile(self.event_log_file, self.event_log_file + '.bk')
            self.event_log = pd.DataFrame.from_csv(self.event_log_file, index_col='wall_time')
        else:
            self.event_log = pd.DataFrame(columns=self.event_log_columns)
            self.event_log.set_index('wall_time', inplace=True)
        logger.debug("File ready for writing")

    def get_log_file_name(self):
        import os
        dirname = os.path.dirname(self.scheme_file)
        basename, _ = os.path.splitext(os.path.basename(self.scheme_file))
        filename = os.path.join(dirname, basename + '_log.csv')
        return filename

    def get_scheme_trial_info(self):
        try:
            s = self.scheme.ix[self.cur_scheduled_run].copy()
            s['sequence_nr'] = self.cur_actual_run
            s['run_nr'] = self.cur_scheduled_run

        except KeyError:
            raise ValueError("trial not present")
        return s

    def get_trial_results_info(self):
        s = self.trials_results.ix[self.cur_actual_run].copy()
        s['sequence_nr'] = self.cur_actual_run
        logger.log(5, "Getting trial {}", self.cur_actual_run)
        return s

    def set_trial_results_info(self, info):
        import datetime
        info['start_date'] = str(datetime.datetime.now())[:-4]
        df_update = pd.DataFrame.from_dict(info, orient='index')
        df_update = df_update.transpose()
        logger.info("updating trial {}".format(info['sequence_nr']))
        logger.info("update info: {}".format(str(info)))
        assert info['sequence_nr'] == self.cur_actual_run

        df_update.set_index('sequence_nr', inplace=True)
        self.trials_results.loc[info['sequence_nr']] = np.NaN
        self.trials_results.update(df_update)

        # complete the results dataframe with info from the scheme dataframe
        r = self.trials_results.loc[info['sequence_nr']].copy()
        r.update(self.scheme.loc[self.cur_scheduled_run])
        self.trials_results.loc[info['sequence_nr']] = r

    def set_trial_finished(self, video_out_filename, video_out_raw_filename):
        if self.comments:
            self.trials_results.loc[self.cur_actual_run]['comments'] = self.comments
        self.trials_results.loc[self.cur_actual_run]['video_out_filename'] = os.path.basename(video_out_filename)
        self.trials_results.loc[self.cur_actual_run]['video_out_raw_filename'] = os.path.basename(video_out_raw_filename)
        self.trials_results.to_csv(self.result_file)
        self.event_log.to_csv(self.event_log_file)
        logger.info("finalized trial {}".format(self.cur_actual_run))
        self.cur_actual_run += 1
        self.cur_scheduled_run += 1

    def set_trial_number(self, i):
        self.cur_scheduled_run = i

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

    def get_video_in_file_name_for_trial(self, trial_no=None):
        if self.video_in_source == "glob":
            dirname = os.path.dirname(self.scheme_file)
            basename, _ = os.path.splitext(os.path.basename(self.scheme_file))
            if trial_no is None:
                trial_no = self.cur_scheduled_run
            file_glob = self.video_in_glob.format(prefix=basename, trial=trial_no)
            file_glob = os.path.join(dirname, file_glob)
            file_list = glob.glob(file_glob)
            file_list.sort()
            logger.debug("used glob {} and got file list {}".format(file_glob, file_list))
            filename = file_list[-1]  # we are using the most recent available file with that
            # trial number
        else:
            raise ValueError("Unknown video in mode {}".format(self.video_in_source))
        return filename

    def get_video_out_file_name_for_trial(self):
        dirname = os.path.dirname(self.scheme_file)
        basename, _ = os.path.splitext(os.path.basename(self.scheme_file))
        scheduled_run_no_str = str(self.cur_scheduled_run).zfill(4)
        actual_run_no_str = str(self.cur_actual_run).zfill(4)
        codes = {'live': 'L', 'video': 'V'}
        mode_code = codes[self.mode]
        date_string = self.make_datetime_string(datetime.datetime.now())
        filename = os.path.join(dirname, basename + '_t' + scheduled_run_no_str + '_r' + actual_run_no_str +
                                mode_code + date_string + '.avi')
        filename_raw = self.make_raw_filename(filename)
        logger.info("Saving video to file {}".format(filename))
        return filename, filename_raw

    def set_event(self, ts, frame_no, msg, *extra_data):
        import time
        start_stop = bool(int(msg[-1]))
        msg = msg[:-1]
        row = [ts, frame_no, self.cur_actual_run, msg, start_stop]
        row.extend(extra_data)
        self.event_log.loc[time.time()] = row

    def get_events_for_trial(self, i=None):
        if i is None:
            i = self.cur_actual_run
        lt = self.event_log.loc[self.event_log['sequence_nr'] == float(i)]
        if not lt.empty:
            assert lt.iloc[0]['type'] == 'TR'
            assert lt.iloc[-1]['type'] == 'TR'
            assert lt.iloc[1:-1]['type'].all() != 'TR'
            assert lt.iloc[0]['start_stop']
            assert not lt.iloc[-1]['start_stop']
        return lt

    def get_scheme_trial(self, i=None):
        if i is None:
            i = self.cur_scheduled_run
        return self.scheme.loc[i]

    def update_results_with_extra_data(self, info):
        info['sequence_nr'] = self.cur_actual_run
        df_update = pd.DataFrame.from_dict(info, orient='index')
        df_update = df_update.transpose()
        df_update.set_index('sequence_nr', inplace=True)
        # self.trials_results.loc[info['sequence_nr']] = np.NaN
        self.trials_results.update(df_update)

    def analyze_trial(self):  # TODO To subclass
        # noinspection PyUnresolvedReferences
        import neuroseries as nts
        lt = self.get_events_for_trial()
        info = self.get_scheme_trial_info()
        logger.info("Analyzing trial {}".format(self.cur_actual_run))
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
        self.cur_actual_run += 1

    # unreferenced
    # def skip_sequence_number(self):
    #     self.cur_actual_run += 1
    #     res = self.trials_results
    #     res.reset_index(inplace=True)
    #     res.ix[len(res) - 1, 'sequence_nr'] = 4
    #     res.set_index('sequence_nr', inplace=True)

    def skip_trial(self):
        self.cur_scheduled_run += 1

    def close(self):
        self.event_log.to_csv(self.event_log_file)
        self.trials_results.to_csv(self.result_file)
        logger.info("Closed csv files")