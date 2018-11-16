from setuptools import setup, find_packages

import os
import subprocess
import glob
import appdirs
from score_behavior import appauthor, appname


current_path = os.getcwd()
try:
    GIT_VERSION = subprocess.check_output(["git", "describe"]).strip().decode('utf-8')
    VERSION = GIT_VERSION.split('-')[0]
except subprocess.CalledProcessError as e:
    GIT_VERSION = "0.1"
    VERSION = GIT_VERSION

os.chdir(current_path)

here = os.getcwd()

with open(os.path.join(here, 'score_behavior', 'VERSION'), 'w') as f:
    f.write(GIT_VERSION)

# Get the long description from the README file
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

object_files = glob.glob('score_behavior/resources/objects/*')

object_dir = os.path.join(appdirs.user_data_dir(appname, appauthor), 'objects')

setup(description='Behavioral scorer',
      long_description=long_description,
      author='Francesco Battaglia',
      author_email='fpbattaglia@gmail.com',
      version=VERSION,
      license='GPLv3',
      packages=find_packages(),
      include_package_data=True,
      data_files=[(object_dir, object_files)],
      name='score_behavior',
      entry_points="""
        [console_scripts]
        score=score_behavior.score_window:_main
      """)
      #install_requires=['pandas', 'appdirs', 'neuroseries', 'PyQt5', 'numpy'])
