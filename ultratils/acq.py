# Class that defines an acquisition.

import os
import re
from datetime import datetime
import numpy as np
import audiolabel
import ultratils.pysonix.bprreader

# Regex that matches a timezone offset at the end of an acquisition directory
# name.
utcoffsetre = re.compile(r'([+-]\d{4})$')

tstamp_format = '%Y-%m-%dT%H%M%S'

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

    def __init__(self,
        datetime_obj, utcoffset, imaging_params=None,
        versions=None, stimulus=None, n_pulse_idx=None,
        n_raw_data_idx=None, pulse_max=None, pulse_min=None,
        n_frames=None, bad_data=None, image_h=None,
        image_w=None, probe=None
    ):
        self.datetime = datetime_obj
        self.utcoffset = utcoffset
        self.imaging_params = imaging_params
        self.versions = versions
        self.stimulus = stimulus
        self.n_pulse_idx = n_pulse_idx
        self.n_raw_data_idx = n_raw_data_idx
        self.pulse_max = pulse_max
        self.pulse_min = pulse_min
        self.n_frames = n_frames
        self.bad_data = bad_data
        self.image_h = image_h
        self.image_w = image_w
        self.probe = probe

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
    dirs = [os.path.normpath(d) for d in os.path.split(path)]
    d = dirs[-1]
    m = utcoffsetre.search(d)
    bad_data = False
    if m is None:
        raise AcqError("Incorrect timestamp for path {:}".format(path))
    else:
        utcoffset = m.groups()[0]
        try:
            dt = datetime.strptime(utcoffsetre.sub('', d), tstamp_format)
        except ValueError:
            raise AcqError("Incorrect timestamp for path {:}".format(path))
    if type == 'bpr':
        try:
            bpr = os.path.join(path, "{:}.bpr".format(d))
            bprreader = ultratils.pysonix.bprreader.BprReader(bpr)
            n_frames = bprreader.header.nframes
            image_h = bprreader.header.h
            image_w = bprreader.header.w
            probe = bprreader.header.probe
        except:
            bad_data = True
            n_frames = None
    else:
        raise AcqError("Unknown type '{:}' specified.".format(type))
        
    params = read_params(os.path.join(path, params_file))
    try:
        with open(os.path.join(path, 'versions.txt')) as f:
            versions = f.read()
    except IOError:
        versions = None
    try:
        with open(os.path.join(path, 'stim.txt')) as f:
            stimulus = f.read()
    except IOError:
        stimulus = None
    try:
        tg = "{:}.sync.TextGrid".format(bpr)
        lm = audiolabel.LabelManager(from_file=tg, from_type='praat')
        durs = [l.duration for l in lm.tier('pulse_idx').search(r'^\d+$')]
        n_pulse_idx = len(durs)
        n_raw_data_idx = len([l for l in lm.tier('raw_data_idx').search(r'^\d+$')])
        pulse_max = np.max(durs)
        pulse_min = np.min(durs)
    except IOError as e:
        n_pulse_idx = None
        n_raw_data_idx = None
        pulse_max = None
        pulse_min = None

    
    return Acq(datetime_obj=dt, utcoffset=utcoffset, imaging_params=params,
        versions=versions, stimulus=stimulus, n_pulse_idx=n_pulse_idx,
        n_raw_data_idx=n_raw_data_idx, pulse_max=pulse_max, pulse_min=pulse_min,
        n_frames=n_frames, bad_data=bad_data, image_h=image_h, image_w=image_w,
        probe=probe
    )
