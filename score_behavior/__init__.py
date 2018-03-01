# Set default logging handler to avoid "No handler found" warnings.
import logging
import os
import subprocess

try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass


current_path = os.getcwd()
try:
    GIT_VERSION = subprocess.check_output(["git", "describe"]).strip().decode('utf-8')
    VERSION = GIT_VERSION.split('-')[0]
except subprocess.CalledProcessError as e:
    here = os.path.dirname(__file__)
    with open(os.path.join(here, 'VERSION')) as f:
        GIT_VERSION = f.read()

appname = "Score"
appauthor = "MemDynLab"
# logging.getLogger(__name__).addHandler(NullHandler())
