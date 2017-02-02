# Generic ultratils utility functions

import os, sys
from datetime import datetime
from dateutil.tz import tzlocal
import numpy as np
import pandas as pd
import ultratils.acq
import audiolabel
from ultratils.pysonix.bprreader import BprReader

def make_acqdir(datadir):
    """Make a timestamped directory in datadir and return a tuple with its 
name and timestamp. Does not complain if directory already exists."""
    tstamp = datetime.now(tzlocal()).replace(microsecond=0).isoformat().replace(":","")
    acqdir = os.path.normpath(os.path.join(datadir, tstamp))
    # This is 'mkdir -p' style behavior.
    try:
        os.makedirs(acqdir)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(acqdir):
            pass
        else:
            print("Could not create {%s}!".format(acqdir))
            raise
    return (acqdir, tstamp)

def extract_frames(expdir, list_filename=None, frames=None):
    """Extract image frames from specified acquisitions and return as a numpy array and
dataframe with associated metadata.

list_filename = filename containing a list of tuple triples, as in frames
frames = list of tuple triples containing an acquisition timestamp string, a
    raw_data_idx frame index, and data type (default is 'bpr')
expdir = the root experiment data directory

Returns an (np.array, pd.DataFrame) tuple in which the array contains the frames of
image data and the DataFrame contains acquisition metadata. The rows of the
DataFrame correspond to the first axis of the array.
"""
    fields = ['stimulus', 'timestamp', 'utcoffset', 'versions', 'n_pulse_idx',
               'n_raw_data_idx', 'pulse_max', 'pulse_min', 'imaging_params',
               'n_frames', 'image_w', 'image_h', 'probe']
    
    if list_filename is not None:
        frames = pd.read_csv(list_filename, sep='\s+', header=None)
    else:
        frames = pd.DataFrame.from_records(frames)
    if frames.shape[1] == 2:
        frames['dtype'] = 'bpr'
    frames.columns = ['tstamp', 'fr_id', 'dtype']

    rows = []
    data = None
    for idx, rec in frames.iterrows():
        a = ultratils.acq.Acq(
            timestamp=rec['tstamp'],
            expdir=expdir,
            dtype=rec['dtype']
        )
        a.gather()
        if idx == 0:
            for v in a.runtime_vars:
                fields.insert(0, v.name)
        if rec['dtype'] == 'bpr':
            rdr = BprReader(a.abs_image_file)
        else:
            raise AcqError('Only bpr data is supported.')

        # Initialize array with NaN on first pass.
        if data is None:
            data = np.zeros([len(frames), rdr.header.h, rdr.header.w]) * np.nan

        # Assume fr_id is a raw_data_idx if it's an integer; otherwise it's a time.
        try:
            if 'fr_id' in frames.select_dtypes(include=['integer']).columns:
                fr_idx = rec['fr_id']
            else:
                lm = audiolabel.LabelManager(
                    from_file=a.abs_sync_tg,
                    from_type='praat'
                )
                fr_idx = int(lm.tier('raw_data_idx').label_at(rec['fr_id']).text)
            data[idx] = rdr.get_frame(fr_idx)
        except Exception as e: 
            fr_idx = None
        row = a.as_dict(fields)
        row['raw_data_idx'] = fr_idx
        rows.append(row)
    return (data, pd.DataFrame.from_records(rows))

def is_white_bpr(bpr_file_name):
    """check for 'white fan of death' BPRs (unusually bright shading and loss of contrast information)."""
    check_bpr = ultratils.pysonix.bprreader.BprReader(bpr_file_name) # select first frame for checking - problem does seem to manifest here.
    frame = check_bpr.get_frame(0)
    if (np.mean(frame) > 200) and (np.var(frame) < 1200):
        return True
    else:
        return False

def is_frozen_bpr(bpr_file_name):
    """check for frozen BPRs (identical frame-to-frame)."""
    check_bpr_first = ultratils.pysonix.bprreader.BprReader(bpr_file_name) # select first and second frames for checking - problem does seem to manifest here.
    frame_first = check_bpr_first.get_frame(0)
    check_bpr_second = ultratils.pysonix.bprreader.BprReader(bpr_file_name)
    frame_second = check_bpr_first.get_frame(1)
    if np.array_equal(frame_first,frame_second):
        return True
    else:
        return False

def is_bad_bpr(bpr_file_name):
    """check for any type of badly recorded BPR."""
    if is_white_fan(bpr_file_name) or is_frozen_fan(bpr_file_name):
        return True
    else:
        return False
