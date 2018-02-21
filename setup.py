try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from score_behavior import GIT_VERSION

setup(description='Behavioral scorer',
      author='Francesco Battaglia',
      author_email='fpbattaglia@gmail.com',
      version=GIT_VERSION,
      license='GPL',
      packages=['score_behavior'],
      package_data={'resources': ['score_behavior/resources/*.*']},
      include_package_data=True,
      name='score_behavior',
      entry_points="""
        [console_scripts]
        scorer32=score_behavior.score:_main
      """, install_requires=['pandas', 'appdirs'])
