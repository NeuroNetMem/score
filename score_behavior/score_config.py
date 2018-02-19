import json
import os.path


_config_dict = {}


def config_init(fname=None):
    config_list = ['/Users/fpbatta/src/batlab/score/score_behavior/resources/score_config.json']  # TODO add proper names for config file
    if fname:
        config_list.append(fname)

    for fn in config_list:
        if os.path.exists(fn):
            f = open(fn)
            d = json.load(f)
            _config_dict.update(d)


def get_config_section(name=None):
    if name in _config_dict:
        return _config_dict[name]
    else:
        return {}
