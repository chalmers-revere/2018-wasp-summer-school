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
Dist = 0.2
r_ref = 120
h_ref = 80
h = 0.
y = 0.
Ka = 0.022
Kp = 0.40
Kd = 0.12
Upperlimit = 0.25
Lowerlimit = -1.0
UpperAngle = 38 / 180. * 3.14
LowerAngle = -38 / 180. * 3.14
y_prev = 320
distances = {"front": 0.0, "left": 0.0, "right": 0.0, "rear": 0.0}
last_distance = 0.
last_radius = 0.
h_prev = 0.
dt = 0.1
T_prev = 0.
LosingObject = False

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

def Saturate(val, Lower, Upper):
    if val < Lower:
        return Lower
    elif val > Upper:
        return Upper
    else:
        return val

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

    # Turn buf into img array (640 * 480 * 4 bytes (ARGB)) to be used with OpenCV.
    img = numpy.frombuffer(buf, numpy.uint8).reshape(480, 640, 4)

    ############################################################################
    # TODO: Add some image processing logic here.

    lowerBound=numpy.array([35,120,86])
    upperBound=numpy.array([40,255,255])

    LosingObject = False

    blurred = cv2.GaussianBlur(img, (11, 11), 0)
    imgHSV = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    # create the Mask
    mask = cv2.inRange(imgHSV,lowerBound,upperBound)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    _,conts,_=cv2.findContours(mask.copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    contour_sizes = [(cv2.contourArea(contour), contour) for contour in conts]
    if len(conts) > 0:
        biggest_contour = max(contour_sizes, key=lambda x: x[0])[1]
        M = cv2.moments(biggest_contour)
        ((_,_),radius) = cv2.minEnclosingCircle(biggest_contour)
        _,_,_,h = cv2.boundingRect(biggest_contour)
        y = int(M["m10"] / M["m00"])
    else:
        LosingObject = True
        y = y_prev
        # radius = last_radius
        # h = h_prev

    distance = distances["front"]

    # print "Current y position:" + str(y)
    print "Current height: " + str(h)
    # cv2.drawContours(img, biggest_contour, -1, (0,255,0), 3)


    # The following example is adding a red rectangle and displaying the result.
    #cv2.rectangle(img, (50, 50), (100, 100), (0,0,255), 2)

    # TODO: Disable the following two lines before running on Kiwi:
    # cv2.imshow("image", img);
    # cv2.imshow("mask", mask);
    # cv2.waitKey(2);

    ############################################################################
    # Example for creating and sending a message to other microservices; can
    # be removed when not needed.
    # angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
    # angleReading.angle = 123.45

    # 1038 is the message ID for opendlv.proxy.AngleReading
    # session.send(1038, angleReading.SerializeToString());
    ea = center - y

    Pa = (ea * Ka) / 180. * 3.14
    Pa = Saturate(Pa, LowerAngle, UpperAngle)

        # UltraSonic 
        # Pd = ed * Kp
        # D = Kd * (dD / dt)

        #image radius
        # Pd = er * Kp
        # D = Kd *(dR / dt)

        #image height * Kp
       
        # print "D: " +str(D)

    if LosingObject == False:
        ed = distance - Dist
        dD = distance - last_distance

        er = (r_ref - radius) / 100.
        dR = (radius - last_radius) / 100.

        eh = (h_ref - h) / 200.
        dh = (h - h_prev) / 200.

        Pd = eh * Kp
        if Pd < 0:
            Pd = Pd * 5
        D = Kd * (dh / dt)

        print "D: "+str(D)

        T = Pd - D
        # if T < 0:
            # T = T * 5

        T = Saturate(T, Lowerlimit, Upperlimit)

    # print "Steering: " + str(Pa)
        last_distance = distance
        last_radius = radius
        y_prev = y
        h_prev = h

    else:
        T = 0

    print "Acceleration: " + str(T)
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
    # if T * T_prev >= 0:
    pedalPositionRequest.position = T
    session.send(1086, pedalPositionRequest.SerializeToString());
    # else:
    #     for i in range(T_prev, T, (T - T_prev) / 4.):
    #         pedalPositionRequest.position = i
    #         session.send(1086, pedalPositionRequest.SerializeToString());
