import os
import pandas as pd

from score_behavior.score_session_manager import SessionManager

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
        self.extra_trial_columns.extend(['loc_1', 'loc_2', 'obj'])
        self.object_files = {}
        self.test_object_images()

    def get_object_files(self):
        return self.object_files

    def test_object_images(self):
        """test that all the object images are there before starting the session"""
        import imghdr
        obj_idxs = list(pd.unique(self.scheme['obj']))
        self.object_dir = os.path.expanduser(self.object_dir)
        self.object_files = {}
        for obj_idx in obj_idxs:
            fname = os.path.join(self.object_dir, str(obj_idx) + '.JPG')
            if not os.path.exists(fname):
                raise RuntimeError("Object image file {} in folder {} does not exist".format(fname, self.object_dir))
            if imghdr.what(fname) != 'jpeg':
                raise RuntimeError("File {} is not a JPG image".format(fname))
            self.object_files[obj_idx] = fname

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

        extra_info = {'loc_1_time': explore_time[loc_1],
                      'loc_2_time': explore_time[loc_2],
                      'loc_1_time_5': explore_time_5[loc_1],
                      'loc_2_time_5': explore_time_5[loc_2]}

        self.update_results_with_extra_data(extra_info)
