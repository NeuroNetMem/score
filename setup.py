try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(description='Behavioral scorer',
      author='Francesco Battaglia',
      author_email='fpbattaglia@gmail.com',
      version='0.3',
      license='GPL',
      packages=['scorer_gui'],
      package_data={'resources': ['scorer_gui/resources/*.*']},
      include_package_data=True,
      name='scorer_gui',
      entry_points="""
        [console_scripts]
        scorer32=scorer_gui.obj_scorer:_main
      """, install_requires=['pandas'])
