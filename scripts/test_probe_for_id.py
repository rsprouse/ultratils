#!/usr/bin/env python

# Test Probe class.

import ultratils.pysonix.probe

probe_type = 19

probe = ultratils.pysonix.probe.Probe(probe_type)

print "Name: ", probe.name
