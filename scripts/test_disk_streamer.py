#!/usr/bin/env python

# Test use of disk_streamer.

import ultratils.disk_streamer
import subprocess
import time

streamer = ultratils.disk_streamer.DiskStreamer('test.wav', channels=1, separate=False)

start = time.time()

streamer.start_stream()

proc = subprocess.Popen('./scripts/wait_for_input')
print proc.poll()
while proc.poll() is None:
    time.sleep(0.1)

streamer.stop_stream()
streamer.close()
