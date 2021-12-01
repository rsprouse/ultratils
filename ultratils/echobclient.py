# Client for communicating with echobserv.

import win32file

class EchoBClient(object):
    def __init__(self):
        self._hpipe = None   # handle to named pipe
        self._pipename = r'\\.\pipe\echocomm' 

    def connect(self):
        self._hpipe= win32file.CreateFile(
            self._pipename,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, 
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )

    def start_acq(self, acqdir):
        outmsg = u"START " + acqdir
        try:
            win32file.WriteFile(self._hpipe, outmsg)
        except TypeError:
            win32file.WriteFile(self._hpipe, outmsg.encode('utf-8'))
        # Read acknowledgment from echobserv.
        (hr, inmsg) = win32file.ReadFile(self._hpipe, 1024)
        return inmsg

    def stop_acq(self):
        outmsg = u"STOP"
        try:
            win32file.WriteFile(self._hpipe, outmsg)
        except TypeError:
            win32file.WriteFile(self._hpipe, outmsg.encode('utf-8'))
        # Read acknowledgment from echobserv.
        (hr, inmsg) = win32file.ReadFile(self._hpipe, 1024)
        return inmsg

    def quit(self):
        '''Send a message to echobserv to quit.'''
        outmsg = u"QUIT"
        try:
            win32file.WriteFile(self._hpipe, outmsg)
        except TypeError:
            win32file.WriteFile(self._hpipe, outmsg.encode('utf-8'))
        self._hpipe.close()
