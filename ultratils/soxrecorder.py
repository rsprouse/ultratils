#!/usr/bin/env python

# Run an ultrasound session on the echoblaster.

import sys
import subprocess
import win32api, win32con

class SoxRecorder(object):
    def __init__(self, wav=None, devicenum=0):
        self.wav = wav
        self.devicenum = devicenum
        self._rec_proc = None

    def stop(self):
        # Send Ctrl-C to sox and ignore it in this script.
        try:
            sys.stderr.write("SoxRecorder: sending ctrl-c to sox\n")
            sys.stderr.flush()
            win32api.GenerateConsoleCtrlEvent(win32con.CTRL_C_EVENT, 0)
            sys.stderr.write("SoxRecorder: sent ctrl-c to sox\n")
            sys.stderr.flush()
        except KeyboardInterrupt:
            sys.stderr.write("SoxRecorder: passing on keyboardinterrupt\n")
            sys.stderr.flush()
            pass
        self._rec_proc.communicate()
        return None
        
    def start(self):
        '''Start recording with sox.'''
        rec_args = [
            'sox.exe',
            '-t', 'waveaudio', '{:d}'.format(self.devicenum),
            '-c', '2',
            '-b', '16',
            '--no-show-progress',
            self.wav
        ]
        self._rec_proc = subprocess.Popen(
            rec_args,
            stderr=subprocess.PIPE,
            shell=True
        )
