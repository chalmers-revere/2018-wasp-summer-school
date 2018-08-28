#!/usr/bin/env python2

# Copyright (C) 2018 Christian Berger
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

# sysv_ipc is needed to access the shared memory where the camera image is present.
import sysv_ipc
# numpy and cv2 are needed to access, modify, or display the pixels
import os
import time
import numpy as np
import cv2
# OD4Session is needed to send and receive messages
import OD4Session
# Import the OpenDLV Standard Message Set.
import opendlv_standard_message_set_v0_9_6_pb2

from src.detectors import HSVDetector, LBPDetector
from src.hsv_calibrate import hsv_calibrate

from src.controllers import angle_controller, speed_controller
from src.estimators import lowpass

# Global params
local = False
mode = 'detect_cascade' # detect_hsv, detect_cascade, calibrate

################################################################################
# This dictionary contains all distance values to be filled by function onDistance(...).
distances = { "front": 0.0, "left": 0.0, "right": 0.0, "rear": 0.0 }

################################################################################
# This callback is triggered whenever there is a new distance reading coming in.
def onDistance(msg, senderStamp, timeStamps):
    #print "Received distance; senderStamp=" + str(senderStamp)
    #print "sent: " + str(timeStamps[0]) + ", received: " + str(timeStamps[1]) + ", sample time stamps: " + str(timeStamps[2])
    #print msg
    if senderStamp == 0:
        distances["front"] = msg.distance
    if senderStamp == 1:
        distances["left"] = msg.distance
    if senderStamp == 2:
        distances["rear"] = msg.distance
    if senderStamp == 3:
        distances["right"] = msg.distance


# Create a session to send and receive messages from a running OD4Session;
# Replay mode: CID = 253
# Live mode: CID = 112
if mode == 'detect_hsv':
    detector = HSVDetector(preset_path='src/hsv_thresh.npz')
elif mode == 'detect_cascade':
    detector = LBPDetector(preset_path='src/classifier_all_lbp_0.999_600neg.xml')
else:
    detector = None

C_angle = angle_controller(640.0/2.0, 30.0/320.0)
C_speed = speed_controller(0.35, 0.15/0.30, 0.1, 10, 0.05)
Lp_dist = lowpass(0.2)

if local:
    if mode == 'calibrate':
        hsv_cal = hsv_calibrate('src/hsv_thresh.npz')
    CID = 253
else:
    CID = 112

# TODO: Change to CID 112 when this program is used on Kiwi.
session = OD4Session.OD4Session(CID)
# Register a handler for a message; the following example is listening
# for messageID 1039 which represents opendlv.proxy.DistanceReading.
# Cf. here: https://github.com/chalmers-revere/opendlv.standard-message-set/blob/master/opendlv.odvd#L113-L115
messageIDDistanceReading = 1039
session.registerMessageCallback(messageIDDistanceReading, onDistance, opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_DistanceReading)
# Connect to the network session.
session.connect()

################################################################################
# The following lines connect to the camera frame that resides in shared memory.
# This name must match with the name used in the h264-decoder-viewer.yml file.
name = "/tmp/img.argb"
# Obtain the keys for the shared memory and semaphores.
keySharedMemory = sysv_ipc.ftok(name, 1, True)
keySemMutex = sysv_ipc.ftok(name, 2, True)
keySemCondition = sysv_ipc.ftok(name, 3, True)
# Instantiate the SharedMemory and Semaphore objects.
shm = sysv_ipc.SharedMemory(keySharedMemory)
mutex = sysv_ipc.Semaphore(keySemCondition)
cond = sysv_ipc.Semaphore(keySemCondition)

u_angle = 0
u_speed = 0
t_stop = time.time()

bb_h = None
bb_r = None

counter = 0
c_lim = 1

G = lambda x, mu, sig: np.exp((-(x - mu)**2) / (2*(sig**2))) / 2

tick = time.time()

################################################################################
# Main loop to process the next image frame coming in.
while True:
    # Wait for next notification.
    cond.Z()
    #print "Received new frame."

    # Lock access to shared memory.
    mutex.acquire()
    # Attach to shared memory.
    shm.attach()
    # Read shared memory into own buffer.
    buf = shm.read()
    # Detach to shared memory.
    shm.detach()
    # Unlock access to shared memory.
    mutex.release()

    u_angle = 20 * np.pi/180
    u_speed = 0.1

    ############################################################################
    # Example for creating and sending a message to other microservices; can
    # be removed when not needed.
    angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
    angleReading.angle = u_angle

    # 1038 is the message ID for opendlv.proxy.AngleReading
    session.send(1038, angleReading.SerializeToString());

    ############################################################################
    # Steering and acceleration/decelration.
    #
    # Uncomment the following lines to steer; range: +38deg (left) .. -38deg (right).
    # Value groundSteeringRequest.groundSteering must be given in radians (DEG/180. * PI).
    groundSteeringRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_GroundSteeringRequest()
    groundSteeringRequest.groundSteering = u_angle
    session.send(1090, groundSteeringRequest.SerializeToString());

    # Uncomment the following lines to accelerate/decelerate; range: +0.25 (forward) .. -1.0 (backwards).
    # Be careful!
    pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()
    pedalPositionRequest.position = u_speed
    session.send(1086, pedalPositionRequest.SerializeToString());

