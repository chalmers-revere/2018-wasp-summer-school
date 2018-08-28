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

# Importing time to catch timestamps of the incoming events (needed for PID controllers)
import time

#######################################################################################
#################### OUR CUSTOM DECLARATIONS ##########################################
#######################################################################################

# 1. Declarations for controlling acceleration
distance = None # current distance CHECK ME None
distance_old = None
referenceDistance = 0.2 # what distance to keep from the target object

K_acc = 0.1 #0.1
Td_acc = 0.05 #0.05
speedLimit = 0.4
u_acc = 0
u_acc_real = 0
u_acc_real_old = 0

distances = { "front": 0.0, "left": 0.0, "right": 0.0, "rear": 0.0, "last_distance_received_time":None }; # This dictionary contains all distance values to be filled by function onDistance(...).

relativeTime = None #current time
relativeTime_old = None #previous time
dTime = None # delta time

# 2. Defining the color boundaries for detecting the sticky note
greenColorLowerBound=numpy.array([35,80,125])
greenColorUpperBound=numpy.array([50,255,255])
obj_on_image_distance  = None
obj_real_height = 10*10 # in mm, width is the same 
#camera related stuff to detect distance to the obj
focal_length = 3.04 # taken from raspberry pi web site 
photo_sensor_resolution_height = 2464.0
photo_sensor_height = 2.76 #taken from raspberry pi web site
pixel_per_mm = photo_sensor_resolution_height/photo_sensor_height 

# 3. Angle related declarations
max_angle = 38 #in degrees
min_angle = -38 #in degrees
max_angle_in_radians = (max_angle/180.0)*numpy.pi
min_angle_in_radians = (min_angle/180.0)*numpy.pi

angle_kp = 0.5 # used in PID controller
angle_default_value = 0 # we don't want the car to turn anywhere, when there is no error in its position, i.e. when the sticky note is exactly in the center of the camera view

##################### END OF OUR CUSTOM DECLARATIONS ###################################
#########################################################################################

# This callback is triggered whenever there is a new distance reading coming in.
def onDistance(msg, senderStamp, timeStamps):
    #print "Received distance; senderStamp=" + str(senderStamp)
    #print "sent: " + str(timeStamps[0]) + ", received: " + str(timeStamps[1]) + ", sample time stamps: " + str(timeStamps[2])
    #print msg
    if senderStamp == 0:
        distances["front"] = msg.distance
        distances["last_distance_received_time"] = time.time()
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
    #print ">>>>> Received new frame."

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

    ###########################################################################
    ###########################################################################
    ###################### OUR CUSTOM LOGIC ###################################
    ###########################################################################

    # STEP 1. Detecting the green sticky note logic 
    # STEP 1.1. changing to HSV 
    imgHSV = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    # STEP 1.2. creating a mask to detect green color
    mask = cv2.inRange(imgHSV,greenColorLowerBound,greenColorUpperBound)
    # STEP 1.2 chech the masked image
    #cv2.imshow("mask",mask)    

    # STEP 1.3 applying masks to get rid of random noise
    kernelOpen=numpy.ones((5,5))
    kernelClose=numpy.ones((20,20))

    maskOpen=cv2.morphologyEx(mask,cv2.MORPH_OPEN,kernelOpen)
    maskClose=cv2.morphologyEx(maskOpen,cv2.MORPH_CLOSE,kernelClose)

    #cv2.imshow("maskClose",maskClose)
    #cv2.imshow("maskOpen",maskOpen)

    # STEP 1.4 Detecting the contour of the sticky note 
    maskFinal=maskClose
    img_new, conts,h=cv2.findContours(maskFinal.copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    steering_value = None # if nothing going to be found, just keep steering == nonde, we do not even send a steering request in such a case 
    obj_on_img_distance = None
    # if contour was actually found::: 
    if (len(conts) > 0):
        cv2.drawContours(img,conts,-1,(255,0,0),3)

        # STEP 1.5 compute the center of the contour
        c = max(conts, key = cv2.contourArea)# FIXME::: find the biggest cont, coz we detect several contours
        M = cv2.moments(c)
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        cv2.circle(img, (cX, cY), 7, (255, 255, 255), -1)
        cv2.putText(img, "center", (cX - 20, cY - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # STEP 1.6. computing teh center of the image
        height, width = img.shape[:2]
        image_cX = width/2 
        image_cY = height/2
        cv2.circle(img, (image_cX, image_cY), 7, (255, 255, 255), -1)

        #STEP 1.7 ensure that it is the obj we are looking for. CALCULATE THE AREA OF THE OBJECT
        area = cv2.contourArea(c)
        hull = cv2.convexHull(c)
        hull_area = cv2.contourArea(hull)
        solidity = area/hull_area
        print ">>>>>  CALC:: " + str(obj_real_height) + " area " + str(area) + " hull_area " + str(hull_area) + " solidity " + str(solidity)

        if solidity > 0.90:
            #STEP 1.8. computing which direction to go based on the identified center of the sticky note
            position_error = image_cX - cX

            # STEP 1.9 computing the angle to output to the motor, using PID controller
            steering_value = angle_kp*position_error/image_cX + angle_default_value # P_out = Kp*position_error + angle_default_value. Dividing with image_cX coz the we want to turn to max angle only when the error is max --> image_cX
        
            # STEP 1.10 CALCULATING THE DISTANCE TO THE IMAGE 
            x,y,w,h = cv2.boundingRect(c)
            cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),2)
            #obj_on_img_distance = obj_real_height*focal_length*height/(h*photo_sensor_height)
            reduced_resolution_pixel_per_mm =(height*pixel_per_mm)/photo_sensor_resolution_height
            obj_on_img_distance = ((obj_real_height*focal_length/(h/reduced_resolution_pixel_per_mm))/1000) - 0.15 # the result is in mm. -0.15 is the compensation for the location of the camera compared to proxiity sensor
        
        # TODO: Disable the following lines before running on Kiwi:
            #cv2.putText(img, 'pos error >>> ' + str(position_error) + '   steering::' + str(steering_value) + '  distance estimation::: ' + str(obj_on_img_distance), (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2) #printing some debug at the bottom
        #cv2.imshow("initial_image",img)
        #cv2.waitKey(2);

    ############################################################################
    # Example: Accessing the distance readings.
    #print "Front = " + str(distances["front"])
    #print "Left = " + str(distances["left"])
    #print "Right = " + str(distances["right"])
    #print "Rear = " + str(distances["rear"])

    ############################################################################
    # Example for creating and sending a message to other microservices; can
    # be removed when not needed.
    #angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
    #angleReading.angle = 123.45

    # 1038 is the message ID for opendlv.proxy.AngleReading
    #session.send(1038, angleReading.SerializeToString());

    ############################################################################
    # Steering and acceleration/decelration.
    #
    # Uncomment the following lines to steer; range: +38deg (left) .. -38deg (right).
    # Value groundSteeringRequest.groundSteering must be given in radians (DEG/180. * PI).
    #groundSteeringRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_GroundSteeringRequest()
    #groundSteeringRequest.groundSteering = 0
    #session.send(1090, groundSteeringRequest.SerializeToString());

    # Uncomment the following lines to accelerate/decelerate; range: +0.25 (forward) .. -1.0 (backwards).
    # Be careful!
    #pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()
    #pedalPositionRequest.position = 0
    #session.send(1086, pedalPositionRequest.SerializeToString());

    relativeTime_old = relativeTime    
    relativeTime = time.time()

    if relativeTime_old is not None:
        dTime = relativeTime - relativeTime_old

    # STEERING REQUEST
    if steering_value is not None:
        if steering_value > max_angle_in_radians:
            steering_value = max_angle_in_radians
        if steering_value < min_angle_in_radians:
            steering_value = -min_angle_in_radians

        print ">>>>>  SENDING STEERING MESSAGE"
        groundSteeringRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_GroundSteeringRequest()
        groundSteeringRequest.groundSteering = steering_value
        session.send(1090, groundSteeringRequest.SerializeToString());

    # ACCELERATION REQUEST
    if distances["last_distance_received_time"] is not None and (relativeTime - distances["last_distance_received_time"]) > 0.7: # we did not receive any proximity data for 0.5 second --> assume there is nothing on the way
        distances["front"] = None

    distance_old = distance

    if distances["front"] is None:
        distance = None
    else: 
        distance = distances["front"]

    if distance is not None: # we only calculate acc if 1. there was an obj detected on image and 2. we have some proximity data from the sensor
        u_acc = K_acc*(referenceDistance - distance)# P part

        if(dTime is not None and distance_old is not None):
            u_acc = u_acc + Td_acc*(distance_old - distance)/dTime # adding D part

        # Add offset to acceleration
        if u_acc < 0:
            #u_acc = u_acc - 0.08
            u_acc = u_acc - 0.05
        if u_acc > 0:
            #u_acc = u_acc + 0.4
            u_acc = u_acc + 0.37

        # Saturation of control signal
        if u_acc < -0.25*speedLimit:
            u_acc = -0.25*speedLimit
        if u_acc > 1:
            u_acc = 1

        # Smoothing of variations in control signal
        u_acc_real_old = u_acc_real
        if u_acc_real_old < u_acc:
            u_acc_real = min(u_acc_real_old + 0.05, u_acc)
        if u_acc_real_old > u_acc:
            u_acc_real_old = max(u_acc_real_old - 0.05, u_acc)

        print ">>>>>  SENDING ACC MESSAGE"
        pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()
        pedalPositionRequest.position = -u_acc # Change u_acc to u_acc_real to implement smoothing
        session.send(1086, pedalPositionRequest.SerializeToString());

        #print "DISTANCE:" + str(distances["front"])
        #print "U_ACC: " + str(u_acc)
    print ">>>>> TRACKER: " + str(obj_on_img_distance) + "  >>>> PROXY " + str(distances["front"])
    print "U_ACC REAL: " + str(u_acc_real)