# Set default logging handler to avoid "No handler found" warnings.
import logging
import os
import subprocess

current_path = os.getcwd()
try:
    os.chdir(os.path.dirname(__file__))
    GIT_VERSION = subprocess.check_output(["git", "describe"]).strip().decode('utf-8')
except subprocess.CalledProcessError as e:
    GIT_VERSION = "Unknown"
os.chdir(current_path)

try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

appname = "Score"
appauthor = "MemDynLab"
# logging.getLogger(__name__).addHandler(NullHandler())
