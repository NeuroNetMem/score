try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# from score_behavior import GIT_VERSION

setup(description='Behavioral scorer',
      author='Francesco Battaglia',
      author_email='fpbattaglia@gmail.com',
      license='GPL',
      packages=['score_behavior', 'score_behavior.ObjectSpace', 'score_behavior.tracking',
                'score_behavior.tracking.geometry', 'score_behavior.tracking_controller'],
      package_data={'resources': ['score_behavior/resources/*.*']},
      include_package_data=True,
      name='score_behavior',
      entry_points="""
        [console_scripts]
        score=score_behavior.score_window:_main
      """, install_requires=['pandas', 'appdirs'])
