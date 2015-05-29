#!/usr/bin/env python

import struct
import numpy as np
import hashlib

class Header(object):
    def __init__(self, filehandle):
        self.packed_format = 'I'*19
        self.packed_size = 19 * 4
        self.fieldnames = [
            'filetype', 'nframes', 'w', 'h', 'ss', '[ul]', '[ur]',
            '[br]', '[bl]', 'probe', 'txf', 'sf', 'dr', 'ld', 'extra'
        ]
        packed_hdr = filehandle.read(self.packed_size)
        hfields = struct.unpack(self.packed_format, packed_hdr)
        idx = 0
        for field in self.fieldnames:
            if field.startswith('['):
                field = field.replace('[','').replace(']','')
                setattr(self, field, [hfields[idx], hfields[idx+1]])
                idx += 2
            else:
                setattr(self, field, hfields[idx])
                idx += 1

class BprReader:
    def __init__(self, filename, checksum=False):
        self._fhandle = open(filename, 'rb')
        self.header = Header(self._fhandle)
        if self.header.filetype != 2:
            msg = "Unexpected filetype! Expected 2 and got {filetype:d}"
            raise ValueError, msg.format(filetype=self.header.filetype)
        # these data_fmt and framesize values are specific to .bpr
        self.data_fmt = 'B' * (self.header.h * self.header.w)
        self.framesize = 1 * (self.header.h * self.header.w)
        self.csums = [None] * self.header.nframes
        if checksum:
            for idx in range(self.header.nframes):
                print "working on {:d}".format(idx)
                data = self.get_frame()
                csum = hashlib.sha1(data.copy(order="c")).hexdigest()
                if csum in self.csums:
                    "Frame {:d} is a duplicate!".format(idx)
                self.csums[idx] = csum
        self._fhandle.seek(self.header.packed_size)
        self._cursor = self._fhandle.tell()

    def __iter__(self):
        return self

    def next(self):
        '''Get the next image frame.'''
        try:
            self._fhandle.seek(self._cursor)
            packed_data = self._fhandle.read(self.framesize)
            data = np.array(struct.unpack(self.data_fmt, packed_data))
        except struct.error:   # ran out of data to unpack()
            raise StopIteration
        self._cursor = self._fhandle.tell()
        return data.reshape([self.header.w, self.header.h]).T
 
    def get_frame(self, idx=None):
        '''Get the image frame specified by idx. Do not advance the read location of _fhandle.'''
        self._fhandle.seek(self.header.packed_size + (idx * self.framesize))
        packed_data = self._fhandle.read(self.framesize)
        self._fhandle.seek(self._cursor)
        data = np.array(struct.unpack(self.data_fmt, packed_data))
        return data.reshape([self.header.w, self.header.h]).T

    def close(self):
        self._fhandle.close()
