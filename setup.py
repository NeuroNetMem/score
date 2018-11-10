try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os
import subprocess

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


setup(description='Behavioral scorer',
      long_description=long_description,
      author='Francesco Battaglia',
      author_email='fpbattaglia@gmail.com',
      version=VERSION,
      license='GPL',
      packages=['score_behavior', 'score_behavior.ObjectSpace', 'score_behavior.tracking',
                'score_behavior.tracking.geometry', 'score_behavior.tracking_controller'],
      package_data={'resources': ['score_behavior/resources/*.*'],
                    'score_behavior': 'VERSION'},
      include_package_data=True,
      name='score_behavior',
      entry_points="""
        [console_scripts]
        score=score_behavior.score_window:_main
      """, install_requires=['pandas', 'appdirs', 'neuroseries', 'pyqt', 'numpy'])
