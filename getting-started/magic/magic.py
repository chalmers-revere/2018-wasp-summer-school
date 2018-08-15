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
import numpy as np
import cv2
# OD4Session is needed to send and receive messages
import OD4Session
# Load the OpenDLV Standard Message Set.
import opendlv_standard_message_set_v0_9_6_pb2


# Callback for the distance message.
def onDistance(msg, senderStamp, timeStamps):
    print "Got distance; senderStamp=" + str(senderStamp)
    print "sent: " + str(timeStamps[0]) + ", received: " + str(timeStamps[1]) + ", sample time stamps: " + str(timeStamps[2])
    print msg

# Callback for the dynamically injected Python code message.
def onNewPythonCode(msg, senderStamp, timeStamps):
    print "Got new code; senderStamp=" + str(senderStamp)
    print msg


# Create a session to send and receive messages from a running live OD4Session at CID 112.
session = OD4Session.OD4Session(cid=112)

# Register a receiver to handle messageID 1039 which represents opendlv.proxy.DistanceReading.
messageIDDistanceReading = 1039
session.registerMessageCallback(messageIDDistanceReading, onDistance, opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_DistanceReading)

# Register a receiver to handle messageID 1101 which represents opendlv.system.SystemOperationState.
messageIDSystemOperationState = 1101
session.registerMessageCallback(messageIDSystemOperationState, onNewPythonCode, opendlv_standard_message_set_v0_9_6_pb2.opendlv_system_SystemOperationState)

# Connect to the OD4Session.
session.connect()


# Image parameters.
WIDTH = 640
HEIGHT = 480
BYTES_PER_PIXEL = 4

# This name is used to attach to the incoming ARGB image.
sharedMemoryForImageIN = "/tmp/img.argb"
# Obtain the keys for the shared memory and semaphores for the incoming image.
keySharedMemoryIN = sysv_ipc.ftok(sharedMemoryForImageIN, 1, True)
keySemMutexIN = sysv_ipc.ftok(sharedMemoryForImageIN, 2, True)
keySemConditionIN = sysv_ipc.ftok(sharedMemoryForImageIN, 3, True)
# Instantiate the SharedMemory and Semaphore objects for the incoming image.
shmIN = sysv_ipc.SharedMemory(keySharedMemoryIN)
mutexIN = sysv_ipc.Semaphore(keySemConditionIN)
condIN = sysv_ipc.Semaphore(keySemConditionIN)


# This name is used to attach to the outgoing ARGB image.
sharedMemoryForImageOUT = "/tmp/debug.argb"
# Create token file.
open(sharedMemoryForImageOUT, 'a').close()
# Obtain the keys for the shared memory and semaphores for the incoming image.
keySharedMemoryOUT = sysv_ipc.ftok(sharedMemoryForImageOUT, 1, True)
keySemMutexOUT = sysv_ipc.ftok(sharedMemoryForImageOUT, 2, True)
keySemConditionOUT = sysv_ipc.ftok(sharedMemoryForImageOUT, 3, True)
# Instantiate the SharedMemory and Semaphore objects for the incoming image.
shmOUT = sysv_ipc.SharedMemory(keySharedMemoryOUT, sysv_ipc.IPC_CREAT, 0666, WIDTH * HEIGHT * BYTES_PER_PIXEL)
mutexOUT = sysv_ipc.Semaphore(keySemMutexOUT, sysv_ipc.IPC_CREAT, 0666, 1)
condOUT = sysv_ipc.Semaphore(keySemConditionOUT, sysv_ipc.IPC_CREAT, 0666, 1)


# Main loop is waiting for next frame notifications.
while True:
    # Wait for next notification.
    condIN.Z()
    print "Got notified about updated image in shared memory."

    # Lock access to shared memory for the incoming image.
    mutexIN.acquire()
    # Attach to shared memory for the incoming image.
    shmIN.attach()
    # Read shared memory for the incoming image into own buffer.
    buf = shmIN.read()
    # Detach to shared memory for the incoming image.
    shmIN.detach()
    # Unlock access to shared memory for the incoming image.
    mutexIN.release()

    # Turn buf into img array (640 * 480 * 4 bytes (ARGB)).
    img = np.frombuffer(buf, np.uint8).reshape(480, 640, 4)
    # Now, we have the image at hand.

    # TODO: Execute the code that has been received in "onNewPythonCode"

    # The following example is simply displaying an image.
    cv2.rectangle(img, (50, 50), (100, 100), (0,0,255), 2)
    cv2.imshow("image", img);
    cv2.waitKey(2);

    imOut = np.asarray(img, dtype=np.uint8)
    print "Shape " + str(imOut.shape)

    # Lock access to shared memory for the outgoing image.
    mutexOUT.acquire()
    # Attach to shared memory for the outgoing image.
    shmOUT.attach()
    # Read shared memory for the outgoing image into own buffer.
    shmOUT.write(np.getbuffer(imOut))
    # Detach to shared memory for the outgoing image.
    shmOUT.detach()
    # Unlock access to shared memory for the outgoing image.
    mutexOUT.release()
    # Notify waiting processes (first, decrement the condition semaphore as the sleeping processes wait on it to become 0)...
    condOUT.acquire()
    # ...then, increment it again to let the other process fall asleep again.
    condOUT.release()

    # Example for creating and sending a message to other microservices:
    #angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
    #angleReading.angle = 123.45

    # 1038 is the message ID for opendlv.proxy.AngleReading
    #session.send(1038, angleReading.SerializeToString());

