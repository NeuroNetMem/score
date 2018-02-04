try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(description='Behavioral scorer',
      author='Francesco Battaglia',
      author_email='fpbattaglia@gmail.com',
      version='0.3',
      license='GPL',
      packages=['score_behavior'],
      package_data={'resources': ['score_behavior/resources/*.*']},
      include_package_data=True,
      name='score_behavior',
      entry_points="""
        [console_scripts]
        scorer32=score_behavior.score:_main
      """, install_requires=['pandas'])
