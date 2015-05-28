#!/usr/bin/env python

# A simple stream-to-disk audio recorder.

import pyaudio
import os
import re
import wave

class DiskStreamer(object):
    '''A class for streaming microphone audio to disk.'''
    def __init__(self, wavname, width=2, fmt=pyaudio.paInt16, channels=2, rate=44100, separate=True):
# TODO: is it necessary to have both width and fmt?
        p = pyaudio.PyAudio()

        basename = os.path.splitext(wavname)[0]
        if separate:     # Save channels to separate files.
            wav = [None] * channels
            for c in range(0,channels):
                wf = wave.open('{}.ch{:d}.wav'.format(basename, c), 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(fmt))
                wf.setframerate(rate)
                wav[c] = wf
        else:
            wf = wave.open('{}.wav'.format(basename), 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(fmt))
            wf.setframerate(rate)
            wav = [wf]

        self.channels = channels
        self.p = p
        self.wav = wav
        self.separate = separate   # Save channels to separate files.

        def callback(in_data, frame_count, time_info, status):
            for idx in range(len(self.wav)):
                self.wav[idx].writeframes(
                    b''.join(in_data[idx:len(in_data):self.channels])
                )
            return (in_data, pyaudio.paContinue)

        # The input stream (microphone).
        stream = p.open(format=p.get_format_from_width(width),
                        channels=channels,
                        rate=rate,
                        input=True,
                        stream_callback=callback)
        self.stream = stream

    def start_stream(self):
        self.stream.start_stream()

    def stop_stream(self):
        self.stream.stop_stream()

    def stream_is_active(self):
        return self.stream.is_active()

    def close(self):
        self.stream.close()
        for w in self.wav:
            w.close()
        self.p.terminate()


