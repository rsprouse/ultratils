# Class that defines an acquisition.

import os
import re
from datetime import datetime
from dateutil.tz import tzlocal
import numpy as np
import audiolabel
import ultratils.pysonix.bprreader

# Regex that matches a timezone offset at the end of an acquisition directory
# name.
utcoffsetre = re.compile(r'(?P<offset>(?P<sign>[-+])(?P<hours>0\d|1[12])(?P<minutes>[012345]\d))')

tstamp_format = '%Y-%m-%dT%H%M%S'

def timestamp():
    """Create a timestamp for an acquisition, using local time."""
    ts = datetime.now(tzlocal()).replace(microsecond=0).isoformat().replace(":","")
    m = utcoffsetre.search(ts)
    utcoffset = m.group('offset')
    ts = utcoffsetre.sub('', ts)
    return (ts, utcoffset)

class AcqError(Exception):
    """Base class for errors in this module."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class Acq():
    """An ultrasound acquisition."""
    @property
    def dirname(self):
        name = "{:}{:}".format(
              self.datetime.replace(microsecond=0).isoformat().replace(":",""),
              self.utcoffset
        )
        return name

    @property
    def date_str(self):
        return self.datetime.date()

    @property
    def time_str(self):
        return self.datetime.time()

    def __init__(self, gather=None, type='bpr', timestamp=None, params_file='params.cfg'):
        if gather is not None:
            dirs = [os.path.normpath(d) for d in os.path.split(gather)]
            timestamp = dirs[-1]
            m = utcoffsetre.search(timestamp)
            if m is None:
                raise AcqError("Incorrect timestamp for path {:}".format(gather))
            else:
                utcoffset = m.group()
            try:
                dt = datetime.strptime(utcoffsetre.sub('', timestamp), tstamp_format)
            except ValueError:
                raise AcqError("Incorrect timestamp for path {:}".format(gather))
        self.timestamp = timestamp
        if type == 'bpr':
            try:
                bpr = os.path.join(gather, "{:}.bpr".format(d))
                bprreader = ultratils.pysonix.bprreader.BprReader(bpr)
                self.n_frames = bprreader.header.nframes
                self.image_h = bprreader.header.h
                self.image_w = bprreader.header.w
                self.probe = bprreader.header.probe
            except:
                bad_data = True
                n_frames = None
        else:
            raise AcqError("Unknown type '{:}' specified.".format(type))
        self.params = read_params(os.path.join(gather, params_file))
        try:
            with open(os.path.join(gather, 'versions.txt')) as f:
                self.versions = f.read()
        except IOError:
            self.versions = None
        try:
            with open(os.path.join(gather, 'stim.txt')) as f:
                self.stimulus = f.read()
        except IOError:
            self.stimulus = None
        try:
            tg = "{:}.sync.TextGrid".format(bpr)
            lm = audiolabel.LabelManager(from_file=tg, from_type='praat')
            durs = [l.duration for l in lm.tier('pulse_idx').search(r'^\d+$')]
            self.n_pulse_idx = len(durs)
            self.n_raw_data_idx = len([l for l in lm.tier('raw_data_idx').search(r'^\d+$')])
            self.pulse_max = np.max(durs)
            self.pulse_min = np.min(durs)
        except IOError as e:
            self.n_pulse_idx = None
            self.n_raw_data_idx = None
            self.pulse_max = None
            self.pulse_min = None
#        try:
#            datetime_obj.tzinfo
#            print "has tzinfo"
#            print datetime_obj.tzinfo
#        except AttributeError:
#            print "no tzinfo"
#        self.datetime = datetime_obj
#        self.utcoffset = utcoffset
#        self.stimulus = stimulus
#        self.bad_data = bad_data

def read_params(pfile):
    """Read the parameter configuration file into a dict."""
    comment = re.compile(r'\s*#')
    params = {}
    with open(pfile, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            try:    # Remove comments.
                (assignment, toss) = comment.split(line, 1)
            except ValueError:
                assignment = line
            try:
                (param, val) = assignment.strip().split("=", 1)
                params[param] = val
            except ValueError as e:
                pass
    return params

def load(path, type='bpr', params_file='params.cfg'):
    """Read data from path and construct an Acq object.

path is the name of a timestamped directory that contains the output of
the ultrasession script.

Some of the metadata is constructed from the last portion of the path, and
it is necessary to include that part of the path name when calling load().
In other words, you cannot load data from the current working directory
by passing '.' as the path. Instead you must use the full path or
construct a relative path that includes the timestamped directory name,
e.g. '../2015-05-05T103922-0700'.

"""
    pass
