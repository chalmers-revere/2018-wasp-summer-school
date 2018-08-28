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
import time
# OD4Session is needed to send and receive messages
import OD4Session
# Import the OpenDLV Standard Message Set.
import opendlv_standard_message_set_v0_9_6_pb2
import math

distances = { "front": 0.0, "left": 0.0, "right": 0.0, "rear": 0.0 }
################################################################################
# This callback is triggered whenever there is a new distance reading coming in.
def onDistance(msg, senderStamp, timeStamps):
    #print "Received distance; senderStamp=" + str(senderStamp)
    #print "sent: " + str(timeStamps[0]) + ", received: " + str(timeStamps[1]) + ", sample time stamps: " + str(timeStamps[2])    
    if senderStamp == 0:
        distances["front"] = msg.distance
    if senderStamp == 1:
        distances["left"] = msg.distance
    if senderStamp == 2:
        distances["rear"] = msg.distance
    if senderStamp == 3:
        distances["right"] = msg.distance

def distanceHeightMap(x):
    a = 6165
    b = -0.009352
    c = -6164
    d = -0.009351
    f = a*math.exp(b*x) + c*math.exp(d*x)
    return f

#Learning Color Names for Real-World Applications, Joost van de Weijer
#BGR image to color names
#order of color names: black ,   blue   , brown       , grey       , green   , orange   , pink     , purple  , red     , white    , yellow
def cnLut(img, cn_lut):
    blue = (img[:,:,0]/16.0).astype(numpy.uint16)*256
    green = (img[:,:,1]/16.0).astype(numpy.uint16)*16
    red = (img[:,:,2]/16.0).astype(numpy.uint16)
    idx = red + green + blue
    cn = numpy.take(cn_lut, idx, axis=0)
    return cn

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
# Load color names lut
cn_read = numpy.loadtxt("./w2c_4096.txt")
cn_lut = numpy.delete(cn_read, numpy.array([0,1,2]), axis=1)
green_threshold = 0.23
viz = 0

#Control parameters
K_p_steer=0.001
K_p_distance=0.62
K_d_distance=0.65
desired_steer_ref=320
desired_distance_ref = 0.15
distance_old = 0
control_steering_signal = 0
speed_signal_win = numpy.array((0.0, 0.0, 0.0, 0.0, 0.0))
control_speed_signal = 0
count = 0
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

    # Turn buf into img array (640 * 480 * 4 bytes (ARGB)) to be used with OpenCV.
    img = numpy.frombuffer(buf, numpy.uint8).reshape(480, 640, 4)
    cn_img = cnLut(img[:,:,0:3], cn_lut)
    binary_cn_green = ((cn_img[:,:,5] > green_threshold)*255).astype(numpy.uint8)
    
    # find the colors within the specified boundaries and apply
    # the mask
    kernel = numpy.ones((13,13),numpy.uint8)
    mask = cv2.morphologyEx(binary_cn_green, cv2.MORPH_CLOSE, kernel)
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)

    # Find largest area, save height
    cc_area = -1
    cc_label = -1
    for label in range(1,nlabels-1):
        if cc_area < stats[label, cv2.CC_STAT_AREA]:
            cc_area = stats[label, cv2.CC_STAT_AREA]
            cc_label = label

    ####P controller for steering###########
    if cc_label > 0 and cc_area > 300:
        error_steer=desired_steer_ref-centroids[cc_label,0]
        #if error_steer > -1 and error_steer < 1:
        #    error_steer = 0
        control_steering_signal=K_p_steer*error_steer
        #print(control_steering_signal)
        control_steering_signal = max(min(control_steering_signal, 38.0), -38.0)

        #### PD controller for speed ###
        distance = distanceHeightMap(stats[cc_label, cv2.CC_STAT_HEIGHT])

        error_distance=desired_distance_ref-distance
        error_distance_derivative = -0.5*(distance-distance_old)
        distance_old=distance
        speed_signal=-(K_p_distance*error_distance+K_d_distance*error_distance_derivative)
        speed_signal = max(min(speed_signal, 0.15), -0.65)
        speed_signal_win[count % 5] = speed_signal
        control_speed_signal = sum(speed_signal_win)/5.0

        if control_speed_signal < 0:
            control_speed_signal = control_speed_signal - 0.3
    else:
        control_steering_signal = control_steering_signal*0.95
        #control_speed_signal = control_speed_signal*0.95
    print control_speed_signal, error_distance, distance
    ############################################################################
    # TODO: Add some image processing logic here.

    if viz:
        # The following example is adding a red rectangle and displaying the result.
        left_c = (int(centroids[cc_label,0] - stats[cc_label, cv2.CC_STAT_WIDTH]/2) , int(centroids[cc_label,1] - stats[cc_label, cv2.CC_STAT_HEIGHT]/2))
        right_c = (int(centroids[cc_label,0] + stats[cc_label, cv2.CC_STAT_WIDTH]/2) , int(centroids[cc_label,1] + stats[cc_label, cv2.CC_STAT_HEIGHT]/2))
        cv2.rectangle(img, left_c, right_c, (0,0,255), 2)

        # TODO: Disable the following two lines before running on Kiwi:
        cv2.imshow("image", ((cn_img[:,:,5] > green_threshold)*255).astype(numpy.uint8));
        cv2.waitKey(2);

    ############################################################################
    # Example for creating and sending a message to other microservices; can
    # be removed when not needed.
    angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
    angleReading.angle = 123.45

    # 1038 is the message ID for opendlv.proxy.AngleReading
    session.send(1038, angleReading.SerializeToString());

    ############################################################################
    # Steering and acceleration/decelration.
    #
    # Uncomment the following lines to steer; range: +38deg (left) .. -38deg (right).
    # Value groundSteeringRequest.groundSteering must be given in radians (DEG/180. * PI).
    groundSteeringRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_GroundSteeringRequest()
    groundSteeringRequest.groundSteering = control_steering_signal
    session.send(1090, groundSteeringRequest.SerializeToString());

    # Uncomment the following lines to accelerate/decelerate; range: +0.25 (forward) .. -1.0 (backwards).
    # Be careful!
    pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()
    pedalPositionRequest.position = control_speed_signal
    session.send(1086, pedalPositionRequest.SerializeToString());
    count = count + 1
