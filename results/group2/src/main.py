#!/usr/bin/env python2
# encoding: utf-8
# Copyright (C) 2018 John Törnblom
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import time
import logging
import OD4Session

from opendlv_standard_message_set_v0_9_6_pb2 import \
    opendlv_proxy_DistanceReading as DistanceReading
    
from percept import CameraPerseption
from control import PlatoonController



logging.basicConfig(level=logging.INFO)
session = OD4Session.OD4Session(cid=112)
ctrl = PlatoonController(session)
cam = CameraPerseption(ctrl.on_front_camera)

def on_distance_reading(msg, sensor_id, *args, **kwargs):
    fn = (ctrl.on_front_ultrasonic,
          ctrl.on_left_infrared,
          ctrl.on_rear_ultrasonic,
          ctrl.on_right_infrared)

    return fn[sensor_id](msg.distance)

session.registerMessageCallback(1039, on_distance_reading, DistanceReading)

# launch the system
session.connect()
cam.start()

# idle
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

# halt the system
cam.stop()
