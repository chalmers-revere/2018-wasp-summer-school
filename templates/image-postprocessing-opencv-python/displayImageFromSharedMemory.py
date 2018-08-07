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

# sysv_ipc is needed to access the shared memory
import sysv_ipc
# numpy and cv2 are needed to access and display the pixels
import numpy
import cv2
# OD4Session is needed to send and receive messages
import OD4Session
# Load the OpenDLV Standard Message Set.
import opendlv_standard_message_set_v0_9_6_pb2

# Callback for an example message of interest.
def onMessage(msg, timeStamps):
   print "sent: " + str(timeStamps[0]) + ", received: " + str(timeStamps[1]) + ", sample time stamps: " + str(timeStamps[2])
   print msg


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

# Create a session to send and receive messages from a running OD4Session at
# CID 253 (replay mode); live messages are available at 112).
session = OD4Session.OD4Session(cid=253)
# Register a receiver to handle a message; the following example is listening
# for messageID 1039 which represents opendlv.proxy.DistanceReading
messageIDDistanceReading = 1039
session.registerMessageCallback(messageIDDistanceReading, onMessage, opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_DistanceReading)
# Connect to the session.
session.connect()

# Main loop is waiting for next frame notifications.
while True:
    # Wait for next notification.
    cond.acquire()
    print "Got notified about update in shared memory."

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

    # Turn buf into img array (640 * 480 * 4 bytes (ARGB)).
    img = numpy.frombuffer(buf, numpy.uint8).reshape(480, 640, 4)

    # TODO: Add some image processing logic here.
    # The following example is simply displaying an image.
    cv2.imshow("image", img);
    cv2.waitKey(2);

    # Example for creating and sending a message to other microservices:
    angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
    angleReading.angle = 123.45

    # 1038 is the message ID for opendlv.proxy.AngleReading
    session.send(1038, angleReading.SerializeToString());
