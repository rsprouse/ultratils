# Class that defines an ultrasound experiment.

import os, sys
import re
from datetime import datetime
from dateutil.tz import tzlocal
import numpy as np
import pandas as pd
from ultratils.acq import Acq

# Regex that matches a timezone offset at the end of an acquisition directory
# name.
utcoffsetre = re.compile(r'(?P<offset>(?P<sign>[-+])(?P<hours>0\d|1[12])(?P<minutes>[012345]\d))')

tstamp_format = '%Y-%m-%dT%H%M%S'

# TODO: use pandas Timestamp to do all datetime handling?

# TODO: remove? rename?
def timestamp():
    """Create a timestamp for an acquisition, using local time."""
    ts = datetime.now(tzlocal()).replace(microsecond=0).isoformat().replace(":","")
    m = utcoffsetre.search(ts)
    utcoffset = m.group('offset')
    ts = utcoffsetre.sub('', ts)
    return (ts, utcoffset)

def is_timestamp(s):
    """Check a string to verify that it is a proper Acq timestamp.

Return the utcoffset portion of the string if the string is verified.

Raise an ExpError if the string is not verified.
"""
    m = utcoffsetre.search(s)
    if m is None:
        raise ExpError("Incorrect timestamp for path {:}".format(s))
    else:
        utcoffset = m.group()
    try:
        dt = datetime.strptime(utcoffsetre.sub('', s), tstamp_format)
    except ValueError:
        raise ExpError("Incorrect timestamp for path {:}".format(s))

class ExpError(Exception):
    """Base class for errors in this module."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class Exp():
    """An ultrasound experiment."""

    def __init__(self, expdir=None, lazy=True):
        self.expdir = os.path.normpath(expdir)
        self.abspath = os.path.abspath(self.expdir)
        self.relpath = self.abspath.replace(self.expdir, '')
        self.acquisitions = []
        self.timestamps = []
        self._image_converter = None
        self.gather(lazy=lazy)

    def gather(self, lazy=True):
        """Gather the acquisitions in the experiment."""
        re_sort = False
        for mydir, subdirs, files in os.walk(self.abspath):
            ts = os.path.split(mydir)[-1]
            if ts not in self.timestamps:
                try:
                    is_timestamp(ts)
                except ExpError:
                    continue
                self.acquisitions.append(
                    Acq(
                        timestamp=ts,
                        expdir=self.abspath,
                        image_converter=self._image_converter
                    )
                )
# TODO: there should be error checking of image size here and/or in Acq()
                if self._image_converter is None:
                    a = self.acquisitions[0]
                    self._image_converter = a.image_converter
                self.timestamps.append(ts)
                re_sort = True
        if re_sort is True:
            self.acquisitions.sort(key=lambda a: pd.to_datetime(a.timestamp))
