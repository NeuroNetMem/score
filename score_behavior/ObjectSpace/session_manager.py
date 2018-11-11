import os
import re
import pandas as pd
import appdirs

from score_behavior.score_session_manager import SessionManager
from score_behavior import appauthor, appname
from score_behavior.score_config import get_config_section

import logging

logger = logging.getLogger(__name__)


class ObjectSpaceSessionManager(SessionManager):
    def __init__(self, filename, initial_trial=1, extra_event_columns=None, extra_trial_columns=None,
                 min_free_disk_space=0, mode='live', r_keys=None):
        super(ObjectSpaceSessionManager, self).__init__(filename, initial_trial=initial_trial,
                                                        extra_event_columns=extra_event_columns,
                                                        extra_trial_columns=extra_trial_columns,
                                                        min_free_disk_space=min_free_disk_space,
                                                        mode=mode, r_keys=r_keys)
        self.object_dir = ""
        self.extra_trial_columns.extend(['loc_1', 'loc_2', 'obj'])
        config_dict = get_config_section("data_manager")
        if "object_dir" in config_dict:
            self.object_dir = config_dict["object_dir"]
        application_dir = appdirs.user_data_dir(appname, appauthor)
        self.object_dir = re.sub("APPDIR", application_dir, self.object_dir)
        self.object_dir = os.path.expanduser(self.object_dir)
        logger.info("ObjectSpace: searching for objects in directory: " + self.object_dir)
        print("ObjectSpace: searching for objects in directory: " + self.object_dir)

        self.object_files = {}
        self.test_object_images()

    def get_object_files(self):
        return self.object_files

    def test_object_images(self):
        """test that all the object images are there before starting the session"""
        import imghdr
        obj_idxs = list(pd.unique(self.scheme['obj']))
        self.object_files = {}
        ll = os.listdir(self.object_dir)
        sr = re.compile(r'(.*).JPG', re.IGNORECASE)
        for l in ll:
            m = re.match(sr, l)
            if m:
                self.object_files[int(m.group(1))] = os.path.join(self.object_dir, l)
                if imghdr.what(os.path.join(self.object_dir, l)) != 'jpeg':
                    raise RuntimeError("File {} is not a JPG image".format(l))

        for obj_idx in obj_idxs:
            if obj_idx not in self.object_files:
                raise RuntimeError("Object image file for item {} in folder {} does not exist".format(obj_idx,
                                                                                                      self.object_dir))

    def get_task_specific_result_columns(self):
        return ('start_date', 'loc_1_time', 'loc_2_time', 'total', 'DI',
                'loc_1_time_5', 'loc_2_time_5',
                'total_5', 'DI_5', 'sequence_nr', 'goal', 'video_out_filename',
                'video_out_raw_filename')

    def analyze_trial(self):
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

        total = explore_time[loc_1] + explore_time[loc_2]
        # noinspection PyPep8Naming
        DI = (explore_time[loc_2] - explore_time[loc_1]) / \
             (explore_time[loc_2] + explore_time[loc_1] + 1.e-15)
        total_5 = explore_time_5[loc_1] + explore_time_5[loc_2]
        # noinspection PyPep8Naming
        DI_5 = (explore_time_5[loc_2] - explore_time_5[loc_1]) / \
               (explore_time_5[loc_2] + explore_time_5[loc_1] + 1.e-15)

        extra_info = {'loc_1_time': explore_time[loc_1],
                      'loc_2_time': explore_time[loc_2],
                      'total': total,
                      'DI': DI,
                      'loc_1_time_5': explore_time_5[loc_1],
                      'loc_2_time_5': explore_time_5[loc_2],
                      'total_5': total_5,
                      'DI_5': DI_5}

        self.update_results_with_extra_data(extra_info)
