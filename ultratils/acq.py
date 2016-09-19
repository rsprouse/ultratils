# Class that defines an acquisition.

# TODO: make sure image_reader file handles get cleaned up properly when this object gets cleaned up

import os, sys
import re
from datetime import datetime
from dateutil.tz import tzlocal
from collections import OrderedDict
from collections import namedtuple
import numpy as np
import pandas as pd
import audiolabel
from ultratils.pysonix.bprreader import BprReader
import ultratils.pysonix.probe
import ultratils.pysonix.scanconvert

# These are needed for make_mp4()
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as manimation
import scipy.io.wavfile
import subprocess

# Regex that matches a timezone offset at the end of an acquisition directory
# name.
utcoffsetre = re.compile(r'(?P<offset>(?P<sign>[-+])(?P<hours>0\d|1[12])(?P<minutes>[012345]\d))')

tstamp_format = '%Y-%m-%dT%H%M%S'

# Named tuple used for runtime variables.
RuntimeVar = namedtuple('RuntimeVar', 'name, val')

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

Raise an AcqError if the string is not verified.
"""
    m = utcoffsetre.search(s)
    if m is None:
        raise AcqError("Incorrect timestamp for path {:}".format(s))
    else:
        utcoffset = m.group()
    try:
        dt = datetime.strptime(utcoffsetre.sub('', s), tstamp_format)
    except ValueError:
        raise AcqError("Incorrect timestamp for path {:}".format(s))

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

class AcqError(Exception):
    """Base class for errors in this module."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class RuntimeVars():
    """A class for storing runtime variables."""
    def __init__(self):
        pass

class Acq():
    """An ultrasound acquisition."""
# TODO: remove?
    @property
    def dirname(self):
        name = "{:}{:}".format(
              self.datetime.replace(microsecond=0).isoformat().replace(":",""),
              self.utcoffset
        )
        return name

# TODO: remove?
    @property
    def date_str(self):
        return self.datetime.date()

# TODO: remove?
    @property
    def time_str(self):
        return self.datetime.time()

    @property
    def runtime_vars(self):
        if self._runtime_vars is None:
            try:
                df = pd.read_csv(self.abs_runtime_vars, sep='\s+', header=None)
                (mypath, ts) = os.path.split(self.relpath)
                is_timestamp(ts)
                t = []
                myvars = df.iloc[:,0].tolist()
                myvars.reverse()
                for var in myvars:
                    (mypath, val) = os.path.split(mypath)
                    t.insert(0, RuntimeVar(var, val))
                self._runtime_vars = t
            except IOError:
                if os.path.split(self.relpath)[0] == '/':
                    pass
                else:
                    sys.stderr.write('INFO: no runtime_vars.txt')
        return self._runtime_vars

    @property
    def abspath(self):
        if self._abspath is None:
            for mydir, subdirs, files in os.walk(os.path.abspath(self.expdir)):
                if os.path.basename(mydir) == self.timestamp:
                    self._abspath = os.path.normpath(os.path.abspath(mydir))
                    break
        return self._abspath

    @property
    def abs_sync_tg(self):
        return os.path.join(self.abspath, "{:}.{:}.sync.TextGrid".format(self.timestamp, self.dtype))

    @property
    def abs_image_file(self):
        return os.path.join(self.abspath, "{:}.{:}".format(self.timestamp, self.dtype))

    @property
    def abs_audio_file(self):
        return '{:}.wav'.format(self.abs_image_file)

    @property
    def abs_versions_file(self):
        return os.path.join(self.abspath, "versions.txt")

    @property
    def abs_stim_file(self):
        return os.path.join(self.abspath, "stim.txt")

    @property
    def abs_runtime_vars(self):
        return os.path.join(self.expdir, "runtime_vars.txt")

    @property
    def framerate(self):
        """Return the frames/second."""
        rate = self._framerate
        if rate is None:
            frames = self.sync_lm.tier('pulse_idx').search(r'\w')
            t1 = frames[0].t1
            t2 = frames[-1].t2
            rate = len(frames) / (t2 - t1)
            self._framerate = rate
        return rate

    @property
    def sync_lm(self):
        """The LabelManager for .sync.textgrid."""
        lm = self._sync_lm
        if lm is None:
            lm = audiolabel.LabelManager(
                from_file=self.abs_sync_tg,
                from_type='praat'
            )
            self._sync_lm = lm
        return lm

    @property
    def raw_data_idx(self):
        """The LabelManager 'raw_data_idx' tier."""
        return self.sync_lm.tier('raw_data_idx')

    @property
    def pulse_idx(self):
        """The LabelManager 'pulse_idx' tier."""
        return self.sync_lm.tier('pulse_idx')

    @property
    def image_reader(self):
        """The image reader."""
        rdr = self._image_reader
        if rdr is None:
            if self.dtype == 'bpr':
                rdr = BprReader(self.abs_image_file)
            self._image_reader = rdr
        return rdr

    @property
    def probe(self):
        """A Probe object."""
        probe = self._probe
        if probe is None:
            if self.dtype == 'bpr':
                probe = ultratils.pysonix.probe.Probe(
                    self.image_reader.header.probe
                )
                self._probe = probe
        return probe

    @property
    def image_converter(self):
        """Converter object for converting raw image data to interpolated format."""
        c = self._image_converter
        if c is None:
            if self.dtype == 'bpr':
                c = ultratils.pysonix.scanconvert.Converter(
                    self.image_reader.header,
                    self.probe
                )
                self._image_converter = c
        return c

    def __init__(self, timestamp=None, expdir=None, dtype='bpr', abspath=abspath, image_converter=None):
        self.utcoffset = is_timestamp(timestamp)
        self.timestamp = timestamp
        self.expdir = os.path.normpath(expdir)
        self.dtype = dtype
        self._abspath = abspath
        self._runtime_vars = None
        self.relpath = self.abspath.replace(self.expdir, '')
        self.runvars = RuntimeVars()
        if self.runtime_vars is not None:
            for v in self.runtime_vars:
                setattr(self.runvars, v.name, v.val)
        self._image_reader = None
        self._framerate = None
        self._sync_lm = None
        if image_converter is None:
            self._image_converter = None
        else:
            if image_converter.input_h == self.image_reader.h and \
               image_converter.input_w == self.image_reader.w:
                self._image_converter = image_converter
            else:
                sys.stderr.write('INFO: ignoring non-matching image_converter for acquisition {:}.'.format(timestamp))
                self._image_converter = None
        self._probe = None

    def gather(self, params_file='params.cfg'):
        """Gather the metadata from an acquisition directory."""
        bpr = ''
        if self.dtype == 'bpr':
            try:
                rdr = self.image_reader
            except:
                self.n_frames = None
                self.image_h = None
                self.image_w = None
                self._probe = None
            self.n_frames = rdr.header.nframes
            self.image_h = rdr.header.h
            self.image_w = rdr.header.w
            self._probe = rdr.header.probe
        else:
            raise AcqError("Unknown type '{:}' specified.".format(type))
        try:
            self.imaging_params = read_params(os.path.join(self.abspath, params_file))
        except IOError:
            self.imaging_params = None
        try:
            with open(os.path.join(self.abs_versions_file)) as f:
                self.versions = f.read()
        except IOError:
            self.versions = None
        try:
            with open(os.path.join(self.abs_stim_file)) as f:
                self.stimulus = f.read()
        except IOError:
            self.stimulus = None
        try:
            tg = self.abs_sync_tg
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

    def as_dict(self, fields):
        """Return an ordered dict with the Acq attributes as key/value pairs."""
        d = OrderedDict()
        for fld in fields:
            d[fld] = getattr(self, fld)
        return d

    def frame_at(self, t, convert=False, missing_val=None):
        """Return image frame data at time t. If convert is True, use the acquisition's image_converter to do a scanconvert. If missing_val is True, return a replacement frame if the frame at time t is missing.

By default frame_at() returns a 2D numpy array of image data or None if no image data is available at time t.
If missing_val is not None, frame_at() returns a tuple """
        frame = None
        repfr = None
        l = self.raw_data_idx.label_at(t)
        while True:
            try:
                fidx = int(l.text) # ValueError if 'NA' or ''
                break              # Got a valid time
            except ValueError:
                if missing_val == 'prev':
                    if self.raw_data_idx[0] == l:
                        l = None
                        break
                    else:
                        l = self.raw_data_idx.prev(l)
                elif missing_val == 'next':
                    if self.raw_data_idx[-1] == l:
                        l = None
                        break
                    else:
                        l = self.raw_data_idx.next(l)
                elif missing_val is not None:
                    repfr = self.image_reader.get_frame(0)
                    repfr = (repfr * 0) + missing_val
                    l = None
                    break
                else:
                    l = None
                    break
        if l is not None:
            if l == self.raw_data_idx.label_at(t):
                frame = self.image_reader.get_frame(fidx)
            else:
                repfr = self.image_reader.get_frame(fidx)
        if frame is not None and convert is True:
            frame = self.image_converter.as_bmp(frame)
        if repfr is not None and convert is True:
            repfr = self.image_converter.as_bmp(repfr)
        if missing_val is None:
            return (frame, l)
        else:
            return (frame, l, repfr)

    def make_mp4(self, t1=None, t2=None, outfile=None, metadata={}, fill=True, audio=True, corrected=True):
        """Make an .mp4, starting at t1 and ending at t2. The metadata parameter is a dict suitable for use with the Matplotlib animation ffmpeg writer. If fille is True, insert blank for missing frames. If corrected is False use raw scanline data in rectangular format. If corrected is True interpolate the scanline data to correct for transducer geometry."""
        labels = self.sync_lm.tier('raw_data_idx').tslice(t1=t1, t2=t2)
        blank_intensity = 0
        if self.dtype == 'bpr':
            if corrected is True:
                blankbpr = self.image_converter.default_bpr_frame(blank_intensity)
                blank = self.image_converter.as_bmp(blankbpr).astype(np.uint8)
            else:
                blank = self.image_reader.get_frame(0).astype(np.uint8) * 0
        else:
            raise AcqError(
                "make_mp4() not implemented for acquisition with dtype {}.".format(
                    self.dtype
                )
            )

        # See http://stackoverflow.com/questions/13714454/specifying-and-saving-a-figure-with-exact-size-in-pixels
        # for discussion of how to set the size of a matplotlib figure
        # without a border.
        #imdims = (blank.shape[1] * 0.01, blank.shape[0] * 0.01)
        fig = plt.figure(frameon=False) #, figsize=imdims, dpi=100)
        #fig.set_size_inches(frame.shape[1], frame.shape[0])
        ax = plt.Axes(fig, [0., 0., 1., 1.])
        ax.set_axis_off()
        fig.add_axes(ax)
#ax.imshow(your_image, aspect='normal')
        p = ax.imshow(blank, vmin=0, vmax=255, cmap='Greys_r') #, aspect='normal')

        FFMpegWriter = manimation.writers['ffmpeg']
        writer = FFMpegWriter(
            fps=self.framerate,
            metadata=metadata
        )
        with writer.saving(fig, 'tmp_vid.mp4', 100):
            for l in labels:
                try:
                    rdidx = int(l.text)
                    d = self.image_reader.get_frame(rdidx)
                    if corrected is True:
                        frame = np.flipud(self.image_converter.as_bmp(d).astype(np.uint8))
                    else:
                        frame = np.flipud(d)
                except ValueError:   # l.text is 'NA'
                    frame = blank
                p.set_data(frame)
                plt.show()
                writer.grab_frame()

        if audio is True:
            arate, d = scipy.io.wavfile.read(self.abs_audio_file)
            aidx0 = int(np.round(t1 * arate))
            aidx1 = int(np.round(t2 * arate))
            snip = d[aidx0:aidx1,0]
            scipy.io.wavfile.write('tmp_aud.wav', arate, snip)
            subprocess.check_call([
                'ffmpeg', '-y',
                '-i', 'tmp_vid.mp4',
                '-i', 'tmp_aud.wav',
                '-vcodec', 'copy', '-shortest', '-strict', '-2',
# TODO: remove hardcoded scale values
                '-vf', 'scale=692x350', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                outfile
            ])
            os.remove('tmp_aud.wav')
            os.remove('tmp_vid.mp4')
        else:
            os.rename('tmp_vid.wav', outfile)
