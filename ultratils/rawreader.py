#!/usr/bin/env python

import os, sys
import numpy as np
import hashlib

class RawReader(object):
    '''Class for reading uniform binary ultrasound data from a file.
    The data portion of the file starts at `data_offset` and
    continues to the end of the file. The file contains a series
    of ultrasound images.

    All data values in the file must be of the same dtype.

    The data layout is organized sequentially such that the
    individual points in a scanline vary most rapidly, followed
    by individual scanlines, and finally individual image frames.
    In other words, the first contiguous portion of the data
    contains points from the first scanline of the first frame
    (the point nearest the probe comes first), the next
    contiguous portion contains the second scanline from the
    first frame, and continuing for each scanline. This layout
    repeats for each frame in sequence.

    Parameters
    ----------
    filename : str
    The name of the file to read.

    npoints : int
    The number of points per scanline.

    nscanlines : int
    The number of scanlines in an image frame.
    
    Optional parameters
    -------------------

    dtype : data type (default np.uint8)
    The data type of each measurement point. If data is not in machine
    byte-order, specify endianness in a numpy dtype object, e.g.:

        dt = np.dtype(np.uint16)
        dt.newbyteorder('>')
        rdr = RawReader(..., dtype=dt)

    data_offset : int (default 0)
    The number of header bytes to skip before the data section of the file.
    Default value indicates no header.

    '''
    def __init__(self, filename, npoints, nscanlines, dtype=np.uint8,
data_offset=0, checksum=False):
        self.filename = os.path.abspath(filename)
        self._fhandle = None
        self.npoints = npoints
        self.nscanlines = nscanlines
        self.points_per_frame = npoints * nscanlines
        self.dtype = dtype
        dtypesize = np.dtype(self.dtype).itemsize
        self.framesize = self.points_per_frame * dtypesize
        self.data_offset = data_offset
        self._data = None
        st = os.stat(filename)
        try:
            assert(((st.st_size - self.data_offset) % self.framesize) == 0)
        except AssertionError:
            msg = 'WARNING: Did not find even number of frames for {:}.'.format(
                filename
            )
            sys.stderr.write(msg)
            sys.stderr.write(' File size {:} bytes.'.format(st.st_size))
            sys.stderr.write(' Frame size {:} bytes.'.format(self.framesize))
        self.nframes = np.int((st.st_size - self.data_offset) / self.framesize)
        self._cursor = 0

    @property
    def data(self):
        '''Return all data as 3-dimensional ndarray.'''
        if self._data is None:
            self._cursor = self._fhandle.tell()
            self._fhandle.seek(self.data_offset)
            data = np.fromfile(self._fhandle, self.dtype)
            self._fhandle.seek(self._cursor)
            imdims = [self.nframes, self.nscanlines, self.npoints]
            self._data = np.rot90(data.reshape(imdims), axes=(1, 2))
        return self._data

    @property
    def sha1(self):
        '''
        Return a list of SHA1 checksums for each image frame.
        '''
        csums = [None] * self.nframes
        for idx,frame in enumerate(self):
            csum = hashlib.sha1(frame.copy(order="c")).hexdigest()
            if csum in csums:
                sys.stderr.write("Frame {:d} is a duplicate!".format(idx))
            csums[idx] = csum
        return csums

    # Define __enter__ and __exit__ to create context manager.
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        '''
        Get next frame, used to iterate through the images one at a time.
        You should not make other reads on the file handle while iterating
        through the reader.
        '''
        try:
            data = self._fhandle.read(self.framesize)
            assert(len(data) == self.points_per_frame)
            data = np.fromstring(data, dtype=self.dtype)
        except AssertionError as e:
            if len(data) == 0:
                self._fhandle.seek(self.data_offset)
                raise StopIteration  # ran out of data at end of file
            else:
                raise RuntimeError('Got unexpected number of data points.')
        return np.rot90(data.reshape([self.nscanlines, self.npoints]))
 
    def get_frame(self, idx=None):
        '''
        Get the image frame specified by idx. Do not advance the read
        location of _fhandle.
        '''
        self._fhandle.seek(self.data_offset + (idx * self.framesize))
        data = self._fhandle.read(self.framesize)
        try:
            assert(len(data) == self.points_per_frame)
        except AssertionError:
            raise IndexError('{:}'.format(idx))
        self._fhandle.seek(self._cursor)
        data = np.fromstring(data, self.dtype)
        return np.rot90(data.reshape([self.nscanlines, self.npoints]))

    def open(self):
        self._fhandle = open(self.filename, 'rb')

    def close(self):
        try:
            self._fhandle.close()
            self._fhandle = None
        except Exception as e:
            raise e
