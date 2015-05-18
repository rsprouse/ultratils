import numpy as np
import wave
from contextlib import closing
import audiolabel

NORM_SYNC_THRESH = 0.2  # normalized threshold for detecting synchronizaton signal.
MIN_SYNC_TIME = 0.0005   # minimum time threshold must be exceeded to detect synchronization signal
                         # With pstretch unit sync signals are about 1 ms

# From https://github.com/mgeier/python-audio/blob/master/audio-files/utility.py
def pcm2float(sig, dtype=np.float64):
    '''Convert integer pcm data to floating point.'''
    sig = np.asarray(sig)  # make sure it's a NumPy array
    assert sig.dtype.kind == 'i', "'sig' must be an array of signed integers!"
    dtype = np.dtype(dtype)  # allow string input (e.g. 'f')
    # Note that 'min' has a greater (by 1) absolute value than 'max'!
    # Therefore, we use 'min' here to avoid clipping.
    return sig.astype(dtype) / dtype.type(-np.iinfo(sig.dtype).min)

def loadsync(wavfile, chan):
    '''Load synchronization signal from an audio file channel and return as a normalized
(range [-1 1]) 1D numpy array.'''
    with closing(wave.open(wavfile)) as w:
        nchannels = w.getnchannels()
        assert w.getsampwidth() == 2
        data = w.readframes(w.getnframes())
        rate = w.getframerate()
    sig = np.frombuffer(data, dtype='<i2').reshape(-1, nchannels)
    return (pcm2float(sig[:,chan], np.float32), rate)

def sync_pstretch(sig, threshold, min_run):
    '''Find and return indexes of synchronization points from pstretch unit,
defined as the start of a sequence of elements of at least min_run length,
all of which are above threshold.'''
    # Implementation: Create a boolean integer array where data points that
    # exceed the threshold == 1, below == 0, then diff the boolean array.
    # Sequences of true (above threshold) elements start where the diff == 1,
    # and the sequence ends (falls below threshold) where the diff == -1.
    # Circumfixing the array with zero values ensures there will be an equal
    # number of run starts and ends even if the signal starts or ends with
    # values above the threshold.
    # TODO: auto threshold (%age of max?)
    bounded = np.hstack(([0], sig, [0]))
    thresh_sig = (bounded > threshold).astype(int)
    difs = np.diff(thresh_sig)
    run_starts = np.where(difs == 1)[0]
    run_ends = np.where(difs == -1)[0]
    return run_starts[np.where((run_ends - run_starts) > min_run)[0]]

def sync_no_pstretch(sig):
    '''Find and return indexes of synchronization points from ultrasound unit,
*without* the pstretch unit. Sync points are defined as the signal peaks that
are the higher than all their neighbors that exceed a threshold, which is a
percentage of the signal maximum.'''
    sig = abs(sig)
    bounded = np.hstack(([0], sig, [0]))
    threshold = 0.5 * np.max(sig)
    thresh_sig = (bounded > threshold).astype(int)
    difs = np.diff(thresh_sig)
    run_starts = np.where(difs == 1)[0]
    run_ends = np.where(difs == -1)[0]
    peaks = np.zeros([len(run_starts])
    for idx,(s,e) in enumerate(zip(run_starts, run_ends)):
        peaks[idx] = s + np.argmax(bounded[s:e])
    return peaks
    
def sync2text(wavname, chan, pstretch=True):
    '''Find the synchronization signals in an acquisition's .wav file and
create a text file that contains frame numbers and time stamps for each pulse.

chan = channel number where sync signal is found (0 == first channel)
pstretch = flag to choose sync algorithm, depending on whether pstretch unit was used
'''
    (syncsig, rate) = loadsync(wavname, chan)
    if pstretch:
        syncsamp = sync_pstretch(syncsig, NORM_SYNC_THRESH, MIN_SYNC_TIME * rate)
    else:
        syncsamp = sync_no_pstretch(syncsig, NORM_SYNC_THRESH, MIN_SYNC_TIME * rate)
    synctimes = np.round(syncsamp * 1.0 / rate, decimals=4)
    print "Found {0:d} synchronization pulses.".format(len(syncsamp))
    dtimes = np.diff(synctimes)
    print "Frame durations range [{0:1.4f} {1:1.4f}].".format(dtimes.min(), dtimes.max())
    outname = wavname.replace('.ch1.wav', '').replace('.ch2.wav','').replace('.wav','')
    txtname = outname + '.sync.txt'
    tgname = outname + '.sync.TextGrid'
    lm = audiolabel.LabelManager()
    intvl_tier = audiolabel.IntervalTier(name="frameidx")
    lm.add(intvl_tier)
    t1 = synctimes[0]
    with open(txtname, 'w') as fout:
        for idx,t in enumerate(synctimes):
            fout.write("{0:0.4f}\t{1:d}\n".format(t,idx))
            try:
                t2 = synctimes[idx+1]
            except IndexError:
                t2 = t + dtimes.min()
            intvl_tier.add(audiolabel.Label(t1=t1, t2=t2, text=str(idx)))
            t1 = t2
    with open(tgname, 'w') as tgout:
        tgout.write(lm._as_string(fmt="praat_long"))
 


