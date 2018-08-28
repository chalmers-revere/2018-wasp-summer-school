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

from time import time
from platform import machine

PLATFORM = machine()

################################################################################
# This dictionary contains all distance values to be filled by function onDistance(...).
distances = { "front": 0.0, "left": 0.0, "right": 0.0, "rear": 0.0 };
distances_prev = { "front": 0.0, "left": 0.0, "right": 0.0, "rear": 0.0 };

################################################################################
# This callback is triggered whenever there is a new distance reading coming in.
def onDistance(msg, senderStamp, timeStamps):
    # print "Received distance; senderStamp=" + str(senderStamp)
    # print "sent: " + str(timeStamps[0]) + ", received: " + str(timeStamps[1]) + ", sample time stamps: " + str(timeStamps[2])
    # print msg
    if senderStamp == 0:
        distances_prev["front"] = distances["front"]
        distances["front"] = msg.distance
    if senderStamp == 1:
        distances_prev["left"] = distances["left"]
        distances["left"] = msg.distance
    if senderStamp == 2:
        distances_prev["rear"] = distances["rear"]
        distances["rear"] = msg.distance
    if senderStamp == 3:
        distances_prev["right"] = distances["right"]
        distances["right"] = msg.distance


# Create a session to send and receive messages from a running OD4Session;
# Replay mode: CID = 253
# Live mode: CID = 112
# TODO: Change to CID 112 when this program is used on Kiwi.
if PLATFORM == "x86_64":
    session = OD4Session.OD4Session(cid=253)
elif PLATFORM == "armv7l":
    session = OD4Session.OD4Session(cid=112)
else:
    print("[ERROR] Unexpected platform: {:s}".format(PLATFORM))
    exit(1)

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

def toDistance(pixels):
    return 32.0/pixels

def white_balance(img):
    result = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    avg_b = numpy.average(result[:, :, 2])
    avg_a = numpy.average(result[:, :, 1])
    result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1)
    result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1)
    result = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
    return result

MAX_STEER          = 38.0/180.0 * numpy.pi
MAX_FORWARD_ACC    = 0.2
MAX_REVERSE_ACC    = 0.6
MIN_DISTANCE_FRONT = 0.2

# controllers
# ACC_P = 0.085
# ACC_D = 0.1
ACC_P = 0.05
ACC_D = 0.075
ACC_REVERSE_P = 0.85
ACC_FORWARD_BIAS = 0.1
ACC_REVERSE_BIAS = 0.4

# lower = numpy.array([ 40,  50,  30])
# upper = numpy.array([100, 255, 255])
lower = numpy.array([ 40,  90,  50])
upper = numpy.array([ 85, 255, 255])

# when was the target seen last
targetLastSeen = 0
targetDistance = 0
previousTargetDistance = 0
previousTime = time()
now = time()

while True:
    # Wait for next notification.
    cond.Z()
    # print "Received new frame."

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

    previousTime = now
    now = time()

    # Turn buf into img array (640 * 480 * 4 bytes (ARGB)) to be used with OpenCV.
    img = numpy.frombuffer(buf, numpy.uint8).reshape(480, 640, 4)
    #imt = white_balance(img)

    ############################################################################
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

    # normalise the v channel
    h, s, v = cv2.split(hsv)
    clahe = cv2.createCLAHE(clipLimit = 2.0, tileGridSize = (8,8))
    s_ = clahe.apply(s)
    v_ = clahe.apply(v)
    hsv_ = cv2.merge((h, s_, v_))

    mask   = cv2.inRange(hsv_, lower, upper)
    kernel = numpy.ones((5,5), numpy.uint8)
    mask   = cv2.erode(mask, kernel, iterations = 3)
    #mask   = cv2.dilate(mask, kernel, iterations = 1)
    res    = cv2.bitwise_and(img, img, mask = mask)

    _, contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    theRect = None
    target  = None
    cv2.drawContours(img, contours, -1, (0, 0, 255))
    for c in contours:
        rect = cv2.boundingRect(c)
        x, y, w, h = rect
        boundingArea = w*h
        contourArea  = cv2.contourArea(c)
        aspectRatio = max(w/h, h/w)
        if (not theRect or boundingArea > theRect[2]*theRect[3]) and h < 160 and w < 160 and boundingArea > 512 and contourArea / boundingArea > 0.75 and aspectRatio < 1.2:
            theRect = rect

    # draw the detected contour
    if theRect:
        targetLastSeen = now
        x, y, w, h = theRect
        previousTargetDistance = targetDistance
        targetDistance = toDistance(h)
        cv2.rectangle(res, (x, y), (x+w, y+h), (0, 255, 0), 2)
        # The following example is adding a red rectangle and displaying the result.
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        target = (x+0.5*w-640/2, y+0.5*h-480/2)


    # TODO: Disable the following two lines before running on Kiwi:
    if PLATFORM == "x86_64":
        cv2.imshow("image", img)
        # cv2.imshow("hsv", hsv)
        # cv2.imshow("hsv'", hsv_)
        cv2.imshow("mask", mask)
        cv2.imshow("res", res)
        cv2.waitKey(2)

    ############################################################################
    # Example: Accessing the distance readings.
    print "Front = " + str(distances["front"])
    print "Left = " + str(distances["left"])
    print "Right = " + str(distances["right"])
    print "Rear = " + str(distances["rear"])

    ############################################################################
    # Example for creating and sending a message to other microservices; can
    # be removed when not needed.
    # angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
    # angleReading.angle = 123.45
    #
    # # 1038 is the message ID for opendlv.proxy.AngleReading
    # session.send(1038, angleReading.SerializeToString());

    timeSinceTargetSeen = now - targetLastSeen
    print("[DEUBG] Time since target seen: {:n}".format(timeSinceTargetSeen))
    print("[DEUBG] Target distance: {:n}".format(targetDistance))

    ############################################################################
    # Steering and acceleration/decelration.
    #
    # Uncomment the following lines to steer; range: +38deg (left) .. -38deg (right).
    # Value groundSteeringRequest.groundSteering must be given in radians (DEG/180. * PI).

    groundSteeringRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_GroundSteeringRequest()

    if target and timeSinceTargetSeen <= 0.5:
        steering = -(38/2)*2*numpy.pi*target[0]/(180*640)
        print("[DEBUG] Steering: " + str(steering))
        groundSteeringRequest.groundSteering = numpy.clip(steering, -MAX_STEER, MAX_STEER)
        session.send(1090, groundSteeringRequest.SerializeToString())

    if timeSinceTargetSeen > 0.5:
        groundSteeringRequest.groundSteering = 0.0
        session.send(1090, groundSteeringRequest.SerializeToString())


    # Uncomment the following lines to accelerate/decelerate; range: +0.25 (forward) .. -1.0 (backwards).
    # Be careful!
    pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()

    TARGET_DISTANCE = 0.35
    if targetDistance > TARGET_DISTANCE and distances["front"] > MIN_DISTANCE_FRONT:
        if timeSinceTargetSeen <= 0.5:
            pedalPositionRequest.position = min(MAX_FORWARD_ACC, ACC_P * (targetDistance - TARGET_DISTANCE)
                                                               + ACC_D * (targetDistance - previousTargetDistance) / (now - previousTime)
                                                               + ACC_FORWARD_BIAS)

            print("[DEBUG] Pedal P: " + str(ACC_P * targetDistance))
            print("[DEBUG] Pedal D: " + str(ACC_D * (targetDistance - previousTargetDistance) / (now - previousTime)))
        else:
            pedalPositionRequest.position = 0.0
    elif distances["front"] < MIN_DISTANCE_FRONT and distances["front"] < distances["rear"]:
        front = (MIN_DISTANCE_FRONT - distances["front"]) / MIN_DISTANCE_FRONT
        back  = min(1.0, distances["rear"] / 0.3)
        pedalPositionRequest.position = max(-MAX_REVERSE_ACC, - ACC_REVERSE_P * front * back - ACC_FORWARD_BIAS)
        # pedalPositionRequest.position = max(-MAX_REVERSE_ACC, ACC_REVERSE_P * (distances["rear"] - distances["front"]) - ACC_REVERSE_BIAS)
    else:
        pedalPositionRequest.position = 0.0

    print("[DEUBG] Pedal position: {:n}".format(pedalPositionRequest.position))
    session.send(1086, pedalPositionRequest.SerializeToString());

    print("[DEBUG] This took {:n}s".format(time()-now))
