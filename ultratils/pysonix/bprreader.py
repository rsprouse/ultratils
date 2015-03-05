#!/usr/bin/env python

import struct
import numpy as np

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
    def __init__(self, filename):
        self._fhandle = open(filename, 'rb')
        self.header = Header(self._fhandle)
        if self.header.filetype != 2:
            msg = "Unexpected filetype! Expected 2 and got {filetype:d}"
            raise ValueError, msg.format(filetype=self.header.filetype)
        # data_fmt and framesize values are specific to .bpr
        self.data_fmt = 'B' * (self.header.h * self.header.w)
        self.framesize = 1 * (self.header.h * self.header.w)
 
    def get_frame(self):
        '''Get the next image frame.'''
# TODO: do something appropriate if there is no more data to read
        packed_data = self._fhandle.read(self.framesize)
        data = np.array(struct.unpack(self.data_fmt, packed_data))
        return data.reshape([self.header.w, self.header.h]).T

    def close(self):
        self._fhandle.close()
