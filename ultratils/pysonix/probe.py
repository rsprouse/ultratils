#!/usr/bin/env python

import xml.etree.ElementTree as ET
import pkg_resources

class Probe:
    '''A class for storing probe parameters.'''
    def __init__(self, probe_id):
        if probe_id != None:
            self.probe_for_id(probe_id)

    def probe_for_id(self, id):
        '''Populate a Probe by id. For now we only get the elements we know we need.'''
        root = ET.fromstring(
            pkg_resources.resource_string('ultratils.pysonix', 'data/probes.xml')
        )
        self.name = root.find('.//probe[@id="{}"]'.format(id)).get('name')
        self.pitch = int(root.find('.//probe[@id="{}"]/pitch'.format(id)).text)
        self.radius = int(root.find('.//probe[@id="{}"]/radius'.format(id)).text)
        self.numElements = int(root.find('.//probe[@id="{}"]/numElements'.format(id)).text)

