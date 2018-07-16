# Class for converting from .bpr (pre-scan converted b-mode data)

import sys
import numpy as np
cimport numpy as np
NPINT = np.int
ctypedef np.int_t NPINT_t
NPFLOAT = np.float
ctypedef np.float_t NPFLOAT_t
NPLONG = np.long
ctypedef np.long_t NPLONG_t

cdef cart2pol(NPFLOAT_t x, NPFLOAT_t y):
    """Convert from cartesian to radian polar coordinates."""
    cdef NPFLOAT_t radius = np.hypot(x,y)
    cdef NPFLOAT_t theta = np.arctan2(y,x)
    return theta, radius

cdef pol2cart(NPFLOAT_t radius, NPFLOAT_t theta):
    """Convert from polar to cartesian coordinates."""
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    return x, y

cpdef scanconvert(np.ndarray[NPLONG_t, ndim=2] Iin, indt=None, indr=None):
    '''Convert data from a .bpr to image data.'''
    framedim = indt.shape
    cdef np.ndarray[NPLONG_t, ndim=2] Iout = np.zeros(framedim, dtype=NPLONG)
    cdef int xCntr, yCntr, indt_, indr_
    for xCntr in np.arange(0, framedim[1]):
        for yCntr in np.arange(0, framedim[0]):
            indt_ = indt[yCntr, xCntr]
            indr_ = indr[yCntr, xCntr]
            if indt_>0 and indt_<Iin.shape[1] and indr_>0 and indr_<Iin.shape[0]:
                Iout[yCntr, xCntr] = Iin[indr_, indt_];
    return Iout

class Converter(object):
    """Converter for bpr to bmp frame data.
On construction this object calculates and caches the mapping from bpr
frame pixels to bmp frame pixels. The as_bmp() method uses the cached
mapping to convert a frame of data.

Sample usage:

converter = Converter(header, probe)
bmpdata = converter.as_bmp(framedata)

"""

    def __init__(self, header, probe, ppmm=2, *args, **kwargs):
        """header = bpr header
probe = Probe object
"""
        super(Converter, self).__init__(*args, **kwargs)
        # TODO EchoB option for input of header/probe values
        self.header = header
        self.input_h = header.h
        self.input_w = header.w
        self.probe = probe

        # apitch, lpitch, radius calculations and ppmm value drawn from
        # ultrasonix matlab code in SonixDataTools.m.

        # For more on these calculations see the Ultrasonix video at
        # https://www.youtube.com/watch?v=I3IBW080ng0

        # speed of sound = 1540 m/s
        # apitch = axial pitch, expressed in distance per time (meters/sec)
        # In the Ultrasonix Matlab code this is calculated as:
        #   handles.header.h/handles.header.sf*1540/2/size(handles.Data,1)
        # where size(handles.Data,1) appears to be the same as header.h, and
        # this simplifies to:
        self.apitch = 1540/2/float(header.sf)
        # lpitch = lateral pitch
        self.lpitch = float(probe.pitch)*1e-6*probe.numElements/header.w
        # probe radius
        self.radius = probe.radius*1e-6
        # pixels per mm; hardcoded value of 2 in SonixDataTools.m
        self.ppmm = ppmm

        # The remaining calculations are drawn from ultrasonix matlab code
        # in scanconvert.m.
        cdef np.ndarray t = np.zeros(header.h, dtype=NPFLOAT)
        t = (np.arange(0,header.w)-header.w/2)*self.lpitch/self.radius
        self.t = t
        self.r = self.radius + np.arange(0,header.h)*self.apitch
        (self.t,self.r) = np.meshgrid(self.t,self.r)
        self.x = self.r*np.cos(self.t)
        self.y = self.r*np.sin(self.t)

        xreg = np.arange(np.min(self.x), np.max(self.x), step=1e-3/self.ppmm)
        yreg = np.arange(np.min(self.y), np.max(self.y), step=1e-3/self.ppmm)
        [yreg, xreg] = np.meshgrid(yreg, xreg)
        theta = np.zeros(xreg.shape, dtype=NPFLOAT)
        rho = np.zeros(xreg.shape, dtype=NPFLOAT)
        indt = np.zeros(xreg.shape, dtype=NPFLOAT)
        indr = np.zeros(xreg.shape, dtype=NPFLOAT)
        # TODO: vectorize?
        bmp_index = []
        bpr_index = []
        for xCntr in np.arange(0, xreg.shape[1]):
            for yCntr in np.arange(0, yreg.shape[0]):
                [theta[yCntr, xCntr], rho[yCntr, xCntr]] = cart2pol(xreg[yCntr, xCntr], yreg[yCntr, xCntr])
                indt = np.int(np.floor(theta[yCntr, xCntr]/(self.lpitch/self.radius)+header.w/2)+1)
                indr = np.int(np.floor((rho[yCntr, xCntr]-self.radius)/self.apitch)+1)
                if indt>0 and indt<header.w and indr>0 and indr<header.h:
                    bmp_index.append(np.ravel_multi_index((yCntr, xCntr), xreg.shape))
                    bpr_index.append(np.ravel_multi_index((indr, indt), (header.h, header.w)))
        self.theta = theta
        self.rho = rho
        self.indt = indt
        self.indr = indr
        self.xreg = xreg
        self.yreg = yreg
        self.bmp_index = bmp_index
        self.bpr_index = bpr_index
        self.bmp = np.zeros(self.xreg.shape, dtype=NPLONG)
        self._fan = np.zeros(self.xreg.shape, dtype=NPLONG)

    def bmp_overlay(self, theta, radius):
        """
            Return points specified in polar (bpr) coordinates as cartesian points that can be plotted over a scanconverted bmp.
            theta = bpr scanline index
            radius = bpr scanline height index
        """
        points = np.zeros(self._fan.shape, dtype=NPLONG) * np.nan
        points.ravel()[theta]
        return points
    
    def convert(self, frame):
        """
            Return unconverted raw data frame as a converted bitmap.
            frame = frame of unconverted data
        """
        self._fan[:] = 0
        if self._fan.dtype != frame.dtype:
            self._fan = self._fan.astype(frame.dtype)
        self._fan.ravel()[self.bmp_index] = frame.ravel()[self.bpr_index]
        return self._fan.astype(frame.dtype, copy=False)

    def convert(self, frame):
        """
            Return bpr or raw frame data as scan-converted ndarray.
            frame = frame of unconverted bpr or raw data
        """
        self._fan[:] = 0
        if self._fan.dtype != frame.dtype:
            self._fan = self._fan.astype(frame.dtype)
        self._fan.ravel()[self.bmp_index] = frame.ravel()[self.bpr_index]
        return self._fan.astype(frame.dtype, copy=False)

    def as_bmp(self, frame):
        """
            Deprecated. Return bpr frame data as a converted bitmap.
            frame = frame of bpr data
        """
        sys.stderr.write("WARNING: as_bmp is deprecated; use convert instead.")
        self.bmp[:] = 0
        self.bmp.ravel()[self.bmp_index] = frame.ravel()[self.bpr_index]
        return self.bmp.astype(frame.dtype, copy=False)
        #data = frame.astype(np.long)
        #return scanconvert(data, indt=self.indt, indr=self.indr)

    def default_bpr_frame(self, default=0):
        """Return a frame of bpr data the same shape as defined by the header, filled with a default value."""
        return  np.zeros([self.header.h, self.header.w]) + default
