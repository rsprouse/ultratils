#!/usr/bin/env python

from distutils.core import setup
import numpy

setup(
  name = 'ultratils',
  packages = ['ultratils', 'ultratils.pysonix'],
  package_data = {'ultratils.pysonix': ['data/probes.xml']},
  scripts = [
    'scripts/bpr2bmp',
    'scripts/psync',
    'scripts/sepchan',
    'scripts/ultraproc',
    'scripts/ultrasession.py',
  ],
  classifiers = [
    'Intended Audience :: Science/Research',
    'Topic :: Scientific/Engineering'
  ]
)
