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
import numpy
import cv2

# OD4Session is needed to send and receive messages
import OD4Session
# Import the OpenDLV Standard Message Set.
import opendlv_standard_message_set_v0_9_6_pb2
 
center = 320
Dist = 0.3
Ka = 0.1
Kp = 1.0
Kd = 0.7
distances = {"front": 0.0, "left": 0.0, "right": 0.0, "rear": 0.0}
last_distance = 0.
dt = 0.1
h_ref = 70

################################################################################
# This callback is triggered whenever there is a new distance reading coming in.
def onDistance(msg, senderStamp, timeStamps):
    # print "Received distance; senderStamp=" + str(senderStamp)
    # print "sent: " + str(timeStamps[0]) + ", received: " + str(timeStamps[1]) + ", sample time stamps: " + str(timeStamps[2])
    # print msg
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
# TODO: Change to CID 112 when this program is used on Kiwi.
session = OD4Session.OD4Session(cid=112)
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

################################################################################
# Main loop to process the next image frame coming in.
while True:
    # Wait for next notification.
    cond.Z()
    print "Received new frame."

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

    # Turn buf into img array (640 * 480 * 4 bytes (ARGB)) to be used with OpenCV.
    img = numpy.frombuffer(buf, numpy.uint8).reshape(480, 640, 4)

    ############################################################################
    # TODO: Add some image processing logic here.
    kernelOpen=numpy.ones((5,5))
    kernelClose=numpy.ones((20,20))
    lowerBound=numpy.array([35,40,70])
    upperBound=numpy.array([95,255,255])

    blurred = cv2.GaussianBlur(img, (11, 11), 0)
    imgHSV = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    # create the Mask
    mask=cv2.inRange(imgHSV,lowerBound,upperBound)

    a,conts,h=cv2.findContours(mask.copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    contour_sizes = [(cv2.contourArea(contour), contour) for contour in conts]
    biggest_contour = max(contour_sizes, key=lambda x: x[0])[1]
    M = cv2.moments(biggest_contour)
    y = int(M["m10"] / M["m00"])
    h = int(M["m01"])

    print "Current y position:" + str(y)
    print "Current distance from Ultrasonic sensor: " + str(distances["front"])
    print "Sticker height: " + str(h)
    # cv2.drawContours(img, biggest_contour, -1, (0,255,0), 3)


    # The following example is adding a red rectangle and displaying the result.
    #cv2.rectangle(img, (50, 50), (100, 100), (0,0,255), 2)

    # TODO: Disable the following two lines before running on Kiwi:
    # cv2.imshow("image", img);
    #cv2.imshow("image", mask);
    # cv2.waitKey(2);

    ############################################################################
    # Example for creating and sending a message to other microservices; can
    # be removed when not needed.
    # angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
    # angleReading.angle = 123.45

    # 1038 is the message ID for opendlv.proxy.AngleReading
    # session.send(1038, angleReading.SerializeToString());


    ea = center - y
    ed = distances["front"] - Dist
    dD = distances["front"] - last_distance
    dh = h_ref - h #if h >

    Pa = ea * Ka

    if ea > 0:
        Pa = -0.3
    else:
        Pa = 0.3

    Pd = ed * Kp
    D = Kd * (dD / dt)

    T = Pd + D

    print "Steering: " + str(Pa)
    print "Acceleration: " + str(T)

    last_distance = distances["front"] 

    ############################################################################
    # Steering and acceleration/decelration.
    #
    # Uncomment the following lines to steer; range: +38deg (left) .. -38deg (right).
    # Value groundSteeringRequest.groundSteering must be given in radians (DEG/180. * PI).
    groundSteeringRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_GroundSteeringRequest()
    groundSteeringRequest.groundSteering = Pa
    session.send(1090, groundSteeringRequest.SerializeToString());

    # Uncomment the following lines to accelerate/decelerate; range: +0.25 (forward) .. -1.0 (backwards).
    # Be careful!
    pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()
    pedalPositionRequest.position = 0.
    session.send(1086, pedalPositionRequest.SerializeToString());