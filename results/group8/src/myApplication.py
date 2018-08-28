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

################################################################################
# This dictionary contains all distance values to be filled by function onDistance(...).
distances = { "front": 0.0, "left": 0.0, "right": 0.0, "rear": 0.0 };

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
################### OUR CONST

#lowerBound = numpy.array([33,80,40])
#upperBound = numpy.array([102,255,255])
lowerBound = numpy.array([35,170,40])
upperBound = numpy.array([90,255,255])
kernelOpen = numpy.ones((20,20))
kernelClose = numpy.ones((20,20))
#control constants for thrust
referenceDistance = 0.40   # unit is meters
Kp_thrust = 0.600/1.0
Kd_thrust = 1.85/1.0 
#control constants for steering
referenceOffset = 320.0    #unit of measurte is pixels
Kp_steer = 0.00055	

################### END OUR CONST

# Create a session to send and receive messages from a running OD4Session;
# Replay mode: CID = 253
# Live mode: CID = 112
# TODO: Change to CID 112 when this program is used on Kiwi.
#session = OD4Session.OD4Session(cid=253)
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

#initialize error distance
distance = 0.0
steer = 0.0
errorDistance = 0.0
errorDistanceUS = 0.0
wasTracking = False
samples = 0

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

    # Turn buf into img array (640 * 480 * 4 bytes (ARGB)) to be used with OpenCV.
    img = numpy.frombuffer(buf, numpy.uint8).reshape(480, 640, 4)

    ############################################################################
    # TODO: Add some image processing logic here.

    # The following example is adding a red rectangle and displaying the result.
    # cv2.rectangle(img, (50, 50), (100, 100), (0,0,255), 2)

################ OUR CODE #######################
    #convert to HSV
    imgHSV=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    #correct image to compendate for luminosity noise
    h,s,v = cv2.split(imgHSV)
    clahe = cv2.createCLAHE(clipLimit=2,tileGridSize=(8,8))
    #h1 = clahe.apply(h)
    s1 = clahe.apply(s)
    v1 = clahe.apply(v)
    imgCL = cv2.merge([h,s1,v1])
    #mask color
    mask=cv2.inRange(imgCL,lowerBound,upperBound)
    ##cv2.imshow("mask",mask)   
    #filter
    maskOpen = cv2.morphologyEx(mask,cv2.MORPH_OPEN,kernelOpen)
    maskClose = cv2.morphologyEx(maskOpen,cv2.MORPH_CLOSE,kernelClose)
    ##cv2.imshow("maskOpen",maskOpen)
    ##cv2.imshow("maskClose",maskClose)
    #track color
    im, conts, h = cv2.findContours(maskClose.copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)

    w_max = 0
    x = 0 
    y = 0
    h = 0
    w = 0
    targetDetected = False 
    #loop over the found green regions and take only the biggest and square shaped
    for i in range(len(conts)) :
        ##cv2.drawContours(img,conts,-1,(255,0,0),3)
        x_tmp,y_tmp,w_tmp,h_tmp=cv2.boundingRect(conts[i])
        #if w_tmp>w_max and float(w_tmp)/float(h_tmp)<1.5 and float(w_tmp)/float(h_tmp)>0.5 :
        if w_tmp>w_max  :
            x = x_tmp 
            y = y_tmp
            h = h_tmp
            w = w_tmp
            w_max = w_tmp
            targetDetected = True 

    ##cv2.rectangle(img,(x,y),(x+w,y+h),(0,0,255),2) 
    ##cv2.circle(img,(int(x+w/2),int(y+h/2)),int((w+h)/4),(0,0,255),2)

    if (targetDetected and distance<2.0):
        #keep old distance error
        errorDistanceOld = errorDistance
        #estimate distance from pixels
        distancePX = 63.35*w**(-1.18)
        distanceUS = distances["rear"]
        if abs(distancePX-distanceUS)<0.20 and abs(steer)<0.3 :
            distance = (distancePX+distanceUS)/2
        else :
            distance = distancePX
        errorDistance = distance - referenceDistance
        #estimate speed error
        errorSpeed = errorDistance - errorDistanceOld
        #angle error in pixels
        errorAngle = referenceOffset - (x+w/2)
        #compute control action
        thrust = Kp_thrust*errorDistance + Kd_thrust*errorSpeed
        if errorDistance<0 :
            thrust = 2.0*thrust
        if thrust>0.15 :
            thrust = 0.15
        #steering control (all on pixels)
        steer = Kp_steer*errorAngle*numpy.sign(thrust)
        steer = min(max(steer,-0.66), 0.66)
        ##cv2.circle(img,(int(320+steer*30),int(240-thrust*150)),20,(0,255,0),2)
        ##print(distanceUS,distancePX,steer,thrust)
        samples = 0
        wasTracking = True
    elif wasTracking and samples<3:
        samples += 1
    else : 
        errorDistanceOld = 0.0
        distance = 0.0
        thrust = 0.0
        steer = 0.0
        wasTracking = False
        samples = 0
    
############################################################################
    # Example: Accessing the distance readings.
    #print "Front = " + str(distances["front"])
    #print "Left = " + str(distances["left"])
    #print "Right = " + str(distances["right"])
    #print "Rear = " + str(distances["rear"])

##################################################

    # TODO: Disable the following two lines before running on Kiwi:
    ##cv2.imshow("image", img);
    ##cv2.waitKey(2);

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
    groundSteeringRequest.groundSteering = steer
    session.send(1090, groundSteeringRequest.SerializeToString());

    # Uncomment the following lines to accelerate/decelerate; range: +0.25 (forward) .. -1.0 (backwards).
    # Be careful!
    pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()
    pedalPositionRequest.position = thrust
    session.send(1086, pedalPositionRequest.SerializeToString());

