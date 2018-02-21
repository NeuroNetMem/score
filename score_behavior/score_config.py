import json
import os
import os.path
import appdirs
import logging

from score_behavior import appauthor, appname


"""
the system will search for config files:
1) in the default user application data folder (changes by OS), under score_config.json
2) in the current directory, under score_config.json
3) the command line argument given by the user

All files in JSON format. Boolean values have to be written as 0 and 1.
Files are processed in this order and the configuration gradually updated 
If a default configuration file was not found in the user_data folder, one is created with the content of the 
string default_config here below.
"""


logger = logging.getLogger(__name__)
default_config = """
{
  "general": {
    "do_track": 1,
    "debug": 1
  },
  "analyzer": {},
  "tracker": {
    "max_num_animals": 1,
    "component_threshold": 40,
    "speed_threshold": 1.2,
    "head_radius": 5,
    "front_radius": 7,
    "back_radius": 10
  },
  "data_manager": {
    "extra_trial_columns": [],
    "extra_event_columns": [],
    "video_in_source": "glob",
    "video_in_glob": "{prefix}_t{trial:0>4}L*_raw.avi",
    "object_dir": ""
  }
}
"""

config_dict = {}


def config_init(fname=None):

    default_loc = os.path.join(appdirs.user_data_dir(appname, appauthor), "score_config.json")

    if not os.path.exists(appdirs.user_data_dir(appname, appauthor)):
        os.mkdir(appdirs.user_data_dir(appname, appauthor))

    if not os.path.exists(default_loc):
        f = open(default_loc, "w")
        f.write(default_config)
        f.close()

    config_list = [default_loc,
                   os.path.join(os.getcwd(), 'score_config.json')]
    if fname:
        config_list.append(fname)

    for fn in config_list:
        if os.path.exists(fn):
            logger.info("Reading configuration information from file {}".format(fn))
            f = open(fn)
            d = json.load(f)
            config_dict.update(d)

    logging.info("Configuration information: {}".format(str(config_dict)))


def get_config_section(name=None):
    if name in config_dict:
        return config_dict[name]
    else:
        return {}
