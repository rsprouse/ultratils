from __future__ import division
import numpy as np
from scipy import ndimage
import scipy.signal as signal
import scipy.io.wavfile

from ultratils.pysonix.bprreader import BprReader

# Algorithms to analyze taptests.

def peakdiff(wavfile):
    '''Find tap by 'peakdiff' algorithm, which finds the peak of the .wav file's first differential.'''
    (rate, audio) = scipy.io.wavfile.read(wavfile)
    atapidx = np.argmax(np.diff(np.abs(audio[:,0]), n=1))
    ataptime = np.float(atapidx) / rate
    return ataptime

def impulse(wavfile):
    '''Find tap by 'impulse' algorithm.'''
    (rate, audio) = scipy.io.wavfile.read(wavfile)

def standard_dev(bprfile, depth, factor):
    '''Find tap in images using 'standard deviation' method, which calculates the standard deviation of the difference of consecutive image frames and chooses the first frame that exceeds a multiple of the mean standard deviation.
depth is the number of rows (closest to the transducer) in which to examine the standard deviation
factor is multiplied by the mean standard deviation to find a threshold'''
# Number of rows in which to check for changes. Row 0 is nearest the transducer.
    rdr = BprReader(bprfile)
    prev = rdr.get_frame(0)[range(depth),:]
    stds = np.zeros([rdr.header.nframes])
    for idx in range(1,rdr.header.nframes):
        frame = rdr.get_frame(idx)[range(depth),:]
        dframe = np.abs(frame - prev)
        stds[idx] = np.std(dframe)
        prev = frame
    
    threshold = factor * np.mean(stds)
    # Find the frame indexes where the threshold is exceeded.
    high = np.where(stds > threshold)[0]
    # Find the first frame index that is not in the first five frames.
    return high[np.where(high > 4)[0][0]]
