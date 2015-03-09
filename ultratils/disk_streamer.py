#!/usr/bin/env python

# A simple stream-to-disk audio recorder.

import pyaudio
import wave

class DiskStreamer(object):
    '''A class for streaming microphone audio to disk.'''
    def __init__(self, wavname, width=2, fmt=pyaudio.paInt16, channels=2, rate=44100):
# TODO: is it necessary to have both width and fmt?
        p = pyaudio.PyAudio()
        
        wf = wave.open(wavname, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(fmt))
        wf.setframerate(rate)

        self.p = p
        self.wf = wf

        def callback(in_data, frame_count, time_info, status):
            self.wf.writeframes(b''.join(in_data))
            return (in_data, pyaudio.paContinue)

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
        self.wf.close()
        self.p.terminate()


