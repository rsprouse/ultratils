#!/usr/bin/env python

from distutils.core import setup
from distutils.extension import Extension
#from Cython.Distutils import build_ext
import numpy

ext_modules = [
  Extension(
    name="ultratils.pysonix.scanconvert",
    sources=["ultratils/pysonix/scanconvert.pyx"],
    libraries = ["m"],
    include_dirs=[numpy.get_include(), "."],
    language="c",
  )
]


setup(
  name = 'ultratils',
#  cmdclass = {'build_ext': build_ext},
#  ext_modules = ext_modules,
  packages = ['ultratils', 'ultratils.pysonix'],
  package_data = {'ultratils.pysonix': ['data/probes.xml']},
  scripts = [
    'scripts/bpr2bmp',
    'scripts/psync',
    'scripts/sepchan',
    'scripts/taptest',
    'scripts/ultraproc',
    'scripts/ultrasession.py',
    'scripts/wait_for_input'
  ],
  classifiers = [
    'Intended Audience :: Science/Research',
    'Topic :: Scientific/Engineering'
  ]
)
