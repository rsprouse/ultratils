#!/usr/bin/env python

import os
import struct
import numpy as np
import hashlib

class RawReader:
    def __init__(self, filename, w, h, pixel_fmt='B', checksum=False):
        self.filename = os.path.abspath(filename)
        self._fhandle = None
        self.open()
        self.w = w
        self.h = h
        self.pixel_fmt = pixel_fmt # format of a single value
        self.data_fmt = '<{:d}{:}'.format(self.h * self.w, pixel_fmt)
        self.framesize = struct.calcsize(self.data_fmt)
        st = os.stat(filename)
        self.nframes = np.int(st.st_size / self.framesize)
        self.csums = [None] * self.nframes
        if checksum:
            for idx in range(self.nframes):
                print("working on {:d}".format(idx))
                data = self.get_frame()
                csum = hashlib.sha1(data.copy(order="c")).hexdigest()
                if csum in self.csums:
                    "Frame {:d} is a duplicate!".format(idx)
                self.csums[idx] = csum
        self._fhandle.seek(0)
        self._cursor = self._fhandle.tell()
        self.close()

    def __iter__(self):
        return self

    def next(self):
        '''Get the next image frame.'''
        if self._fhandle is None:
            self.open()
        try:
            self._fhandle.seek(self._cursor)
            packed_data = self._fhandle.read(self.framesize)
            data = np.array(struct.unpack(self.data_fmt, packed_data))
        except struct.error:   # ran out of data to unpack()
            raise StopIteration
        self._cursor = self._fhandle.tell()
        return data.reshape([self.w, self.h]).T
 
    def get_frame(self, idx=None):
        '''Get the image frame specified by idx. Do not advance the read location of _fhandle.'''
        if self._fhandle is None:
            self.open()
        self._fhandle.seek(idx * self.framesize)
        packed_data = self._fhandle.read(self.framesize)
        self._fhandle.seek(self._cursor)
        data = np.array(struct.unpack(self.data_fmt, packed_data))
        return data.reshape([self.w, self.h]).T

    def open(self):
        self._fhandle = open(self.filename, 'rb')

    def close(self):
        try:
            self._fhandle.close()
            self._fhandle = None
        except Exception as e:
            raise e
