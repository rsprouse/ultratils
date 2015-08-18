#!/usr/bin/env python

# Run an ultrasound session.

# This version works well with ultracomm 0.2.1-alpha.

import os, os.path, sys, subprocess, shutil
import win32api, win32con, win32file
from datetime import datetime
from dateutil.tz import tzlocal
import getopt
import random
#import ultratils.disk_streamer
import time

PROJECT_DIR = r"C:\Users\lingguest\acq"
RAWEXT = ".bpr"

standard_usage_str = '''python ultrasession.py --params paramfile [--datadir dir] [--stims filename] [--stimulus stimulus] [--ultracomm ultracomm_cmd] [--do-log] [--random] [--no-prompt] [--freeze-only] [--no-ultracomm] [--no-audio]'''
help_usage_str = '''python ultrasession.py --help|-h'''

def usage():
    print('\n' + standard_usage_str)
    print('\n' + help_usage_str + '\n')

def help():
    print('''
ultrasession.py: Perform one or more ultrasound acquisitions with the
ultracomm command line utility. Organize output into timestamped folders,
one per acquisition. Postprocess synchronization signal and separate audio
channels into separate speech and synchronization .wav files.
''')
    print('\n' + standard_usage_str)
    print('''
Required arguments:

    --params paramfile
    The name of an parameter file to pass to ultracomm.

Optional arguments:

    --datadir dir
    The name of a directory where acquisitions will be collected.
    Default is %s.

    --stims stimfile
    The name of a file containing stimuli, one per line. Each stimulus
    line will correspond to one acquisition, and the stimulus line will be
    copied to the file stim.txt in the acquisition subdirectory. If no
    stimulus file is provided then ultrasession will perform a single
    acquisition and stop.

    --stimulus stimulus
    A string containing a stimulus token. This string will be copied to
    the stim.txt file in the acquisition subdirectory. When --stimulus is
    provided ultrasession will perform a single acquisition and stop.

    The --stims and --stimulus parameters are alternate ways of running
    ultrasession. The --stims parameter is intended for running a series of
    acquisitions in batch mode from the command line, and the --stimulus
    parameter is more suitable for creating individual acquisitions under
    the control of another application, such as from within a loop in
    an opensesame experiment. If both the --stims and --stimulus parameters
    are provided, the option appearing last in the argument list will
    control the behavior of ultrasession.

    --ultracomm ultracomm_cmd
    The name of the ultracomm command to use to connect the Ultrasonix,
    including path, if desired. If this option is not provided the script
    will default to 'ultracomm'.

    --do-log
    When this option is used ultracomm will produce a logfile that can
    be used for acquisition post-mortem and debugging. The logfile has the
    same name as the output file plus the extension '.log.txt'. No
    logfile is produced if this option is not used.
    
    --random
    When this option is provided stimuli will presented in a
    randomized order. When it is not provided stimuli will be presented they
    appear in the stimulus file.

    --no-prompt
    When this option is provided the operator will not be prompted to
    press the Enter key to start an acquisition. Acquisition will begin
    immediately.
    
    --av-hack
    Attempt to ignore access violation errors in ultracomm.
    
    --freeze-only
    When this option is used then the --freeze-only parameter is sent
    to ultracomm and no acquisition is performed.

    --no-ultracomm
    When this option is provided then the ultracomm utility will not
    run during the acquisition. Thus no .bpr or .idx.txt files will be
    created. The timestamped acquisition directory will be created, and
    the ultracomm parameter file and stim.txt will be created in the
    acquisition directory. Audio will be captured and a .wav file
    created unless the --no-audio paramter is specified.

    --no-audio
    When this option is provided then audio will not be captured during
    the acquisition and no output .wav file will be created.

'''.format(PROJECT_DIR))
    

def freeze(paramsfile, ultracomm_cmd):
    '''Freeze ultrasound.'''
    frz_args = [ultracomm_cmd, '--params', paramsfile, '--freeze-only', '--verbose', '1']
    frz_proc = subprocess.Popen(frz_args)
    frz_proc.communicate()


def run_ultracomm_and_block(args):
    """Run ultracomm, wait for user input, and return ultracomm returncode."""
    sys.stderr.write("ultrasession: running ultracomm with {}".format(args))
    sys.stderr.flush()
    ult_proc = subprocess.Popen(args) #, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pipename = r'\\.\pipe\ultracomm'
    start = time.time()
    fhandle = None
    while not fhandle:
        try:
            fhandle = win32file.CreateFile(pipename, win32file.GENERIC_WRITE, 0, None, win32file.OPEN_EXISTING, 0, None)
        except:
            if ult_proc.poll() is None:
                time.sleep(0.1)
                fhandle = None
                if time.time() - start > 4:
                    sys.stderr.write("ultrasession: throw IOError while opening named pipe\n")
                    sys.stderr.flush()
                    raise IOError("Could not connect to named pipe.")
            else:
                raise RuntimeError("ultracomm stopped with returncode {:d}.".format(ult_proc.returncode))
    # ultracomm creates pipe after imaging is confirmed.
    sys.stderr.write("\n")
    sys.stderr.flush()
    sys.stderr.write("IMAGING\n")
    sys.stderr.flush()

    # Wait for user interaction, then terminate ultracomm.
    raw_input("Press Enter to end ultrasession.")
    
    win32file.WriteFile(fhandle, 'END')
    #ult_proc.wait()
    # When using wait() ultracomm occasionally appeared to hang. A possible reason
    # is that OS pipe buffers overfill, and the subprocess docs warn that this
    # can lead to deadlock. We try communicate() to avoid this deadlock.
    #ult_proc.communicate()
    shutdown_start = time.time()
    while ult_proc.poll() is None:
        time.sleep(0.1)
        if time.time() - shutdown_start > 2:
            # Try this as a last resort.
            ult_proc.terminate()
    sys.stderr.write("EXITING\n")
    sys.stderr.flush()
    return ult_proc.returncode

def kill_rec(rec_proc):
    # Send Ctrl-C to sox and ignore it in this script.
    try:
        sys.stderr.write("ultrasession: sending ctrl-c to sox\n")
        sys.stderr.flush()
        win32api.GenerateConsoleCtrlEvent(win32con.CTRL_C_EVENT, 0)
        sys.stderr.write("ultrasession: sent ctrl-c to sox\n")
        sys.stderr.flush()
    except KeyboardInterrupt:
        sys.stderr.write("ultrasession: passing on keyboardinterrupt\n")
        sys.stderr.flush()
        pass
    rec_proc.communicate()
    return None
    
def acquire(acqname, paramsfile, ultracomm_cmd, skip_ultracomm, skip_audio, do_log, av_hack):
    '''Perform a single acquisition, creating output files based on acqname.'''

    rec_proc = None

    try:
        if skip_audio is False:
            rec_args = ['C:\\bin\\rec.exe', '--no-show-progress', '-c', '2', acqname + '.wav']
            rec_proc = subprocess.Popen(rec_args, stderr=subprocess.PIPE, shell=True)
        # TODO: check for errors running sox.

        ult_args = [ultracomm_cmd, '--params', paramsfile, '--output', acqname, '--named-pipe'] #, '--verbose', '1']
        if do_log is True:
            ult_args.append('--do-log')
        if av_hack is True:
            ult_args.append('--av-hack')

        if skip_ultracomm is False:
            try:
                sys.stderr.write("ultrasession: RUNNING ultracomm\n")
                sys.stderr.flush()
                rc = run_ultracomm_and_block(ult_args)
                print "ultrasession: RAN ultracomm and got {:d}".format(rc)
                sys.stderr.write("ultrasession: RAN ultracomm and got {:d}\n".format(rc))
                sys.stderr.flush()
            except (IOError, RuntimeError, Exception) as e:
                print "ultrasession: Caught an exception while running ultracomm."
                print str(e)
                sys.stderr.write("ultrasession: Caught an Exception while running ultracomm.\n")
                sys.stderr.write("ultrasession: Exception string: " + str(e) + "\n")
                sys.stderr.flush()
            finally:
                if rec_proc is not None:
                    try:
                        rec_proc = kill_rec(rec_proc)
                    except:
                        pass
        else:
            # Wait for user interaction, then terminate ultracomm.
            raw_input("Press Enter to end ultrasession.")
            if rec_proc is not None:
                try:
                    rec_proc = kill_rec(rec_proc)
                except:
                    pass
    except IOError as e:
        sys.stderr.write("ultrasession: ioerror in ultracomm\n")
        sys.stderr.flush()
        if rec_proc is not None:
            try:
                rec_proc = kill_rec(rec_proc)
            except:
                pass
        raise IOError("ultrasession: Could not connect to named pipe.")
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.stderr.write("ultrasession: unknown error in ultracomm\n")
        sys.stderr.flush()
        if rec_proc is not None:
            try:
                rec_proc = kill_rec(rec_proc)
            except:
                pass
        raise RuntimeError("ultrasession: ultracomm ended with an error.")


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:d:s:u:r:h", ["params=", "datadir=", "stims=", "ultracomm=", "do-log", "random", "av-hack", "help", "stimulus=", "no-prompt", "freeze-only", "no-ultracomm", "no-audio"])
    except getopt.GetoptError as err:
        sys.stderr.write(str(err))
        usage()
        sys.exit(2)
    params = None
    datadir = PROJECT_DIR
    stimfile = None
    ultracomm = 'ultracomm'
    do_log = False
    randomize = False
    av_hack = False
    freeze_only = False
    no_prompt = False
    skip_ultracomm = False
    skip_audio = False
    stimulus = ''
    for o, a in opts:
        if o in ("-p", "--params"):
            params = a
        elif o in ("-d", "--datadir"):
            datadir = a
        elif o in ("-s", "--stims"):
            stimfile = a
            stimulus = ''
        elif o in ("-u", "--ultracomm"):
            ultracomm = a
        elif o == '--stimulus':
            stimulus = a
            stimfile = None
        elif o == '--do-log':
            do_log = True
        elif o in ("-r", "--random"):
            randomize = True
        elif o == '--av-hack':
            av_hack = True
        elif o in ("-h", "--help"):
            help()
            sys.exit(0)
        elif o == "--freeze-only":
            freeze_only = True
        elif o == "--no-prompt":
            no_prompt = True
        elif o == "--no-ultracomm":
            skip_ultracomm = True
        elif o == "--no-audio":
            skip_audio = True
    if params is None:
        usage()
        sys.exit(2)
    stims = []
    if stimfile is None:
        stims = [stimulus]
    else:
        with open(stimfile, 'rb') as file:
            for line in file.readlines():
                stims.append(line.rstrip())
    if freeze_only is True:
        freeze(params, ultracomm)
    else:
        if randomize:
            random.shuffle(stims)
        for stim in stims:
            if stimulus != '':
                stim = stimulus
            if no_prompt is False:
                raw_input("Press <Enter> for acquisition.")
            tstamp = datetime.now(tzlocal()).replace(microsecond=0).isoformat().replace(":","")
            acqdir = os.path.join(datadir, tstamp)
            if not os.path.isdir(acqdir):
                try:
                    os.mkdir(acqdir)
                except:
                    print "Could not create {%s}!".format(acqdir)
                    raise
            try:
                if stim != '':
                    print("\n\n******************************\n\n")
                    print(stim)
                    print("\n\n******************************\n\n")
    
                acqbase = os.path.join(acqdir, tstamp + RAWEXT)
                try:
                    copyparams = os.path.join(acqdir, 'params.cfg')
                    print "Copying ", params, " to ", copyparams
                    shutil.copyfile(params, copyparams)
                    with open(os.path.join(acqdir, 'stim.txt'), 'w+') as stimout:
                        stimout.write(stim)
                    acquire(
                        acqbase,
                        params,
                        ultracomm,
                        skip_ultracomm=skip_ultracomm,
                        skip_audio=skip_audio,
                        do_log=do_log,
                        av_hack=av_hack
                    )
                except KeyboardInterrupt:
                    pass   # Ignore Ctrl-C sent during acquire().
                except IOError as e:
                    sys.stderr.write("Could not copy parameter file or create stim.txt! ")
                    sys.stderr.write(str(e) + "\n")
                    raise
            except Exception as e:
                sys.stderr.write("Error in acquiring!\n")
                sys.stderr.write(str(e) + "\n")
                raise
    
#        try:
#            print "Separating audio channels"
#            separate_channels(acqbase)
#        except Exception as e:
#            print "Error in separating audio channels", e
#            raise
#    
#        try:
#            print "Creating synchronization textgrid"
#            wavname = acqbase + '.wav'
#            print "synchronizing ", wavname
#            sync2text(wavname)
#            print "Created synchronization text file"
#        except Exception as e:
#            print "Error in creating synchronization textgrid!", e
#            raise
#
#
