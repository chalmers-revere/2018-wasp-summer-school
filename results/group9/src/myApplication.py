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
from threading import Lock
import time
import sys
import math

lock = Lock()

car = 1  #0=kiwi, 1=snowfox
use_speed = 1

#toggle to get windows
view_image = 0 

use_crop_mode = 1  #1= on, 0 = off, this mode makes the code 20 times faster when processing the images.

cropped_in_y = 320
if car == 0:
	cropped_in_y = 320 #kiwi
else: #car == 1
	cropped_in_y = 450 #snowfox

image_width = 640
image_height = 480

Minimum_height_of_object = 20

dist_front = 0
dist_back = 0
dist_left = 0
dist_right = 0
prev_distance = 0
prev_height = 0
prev_time = 0
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
p1x = 0
p1y = 0
p2x = image_width
p2y = cropped_in_y #480

turn = 0
speed = 0

max_turn_snowfox = 10

center_of_image = 320
max_turn = 0.65
max_speed = 0.14 #0.16
max_reverse_speed = -0.6 #-0.65
height_goal = 70 #70*0.12/max_speed
distance_goal = 2000 #goal in cm

dist_side_to_close = 0.10
dist_front_back_to_close = 0.45*max_speed/0.12
dist_front_back_slow_dist = 0.8
min_speed_front = 0.1
min_speed_back = -0.42 #-0.36

#drive mode variables
drive_mode = 2 #search_mode=2, track_mode = 0, dead_recogning=1, bypass_mode = 3
time_entered_mode = 0
time_in_mode = 0
max_time_in_dead_recogning = 20
max_time_in_search = 0
max_time_search_driving = 3
search_mode = 1 # 0=searching staright forward, 1=searching backward turning
time_entered_search_drive_mode = 0

bypass_mode = 0 #0 turn left 0.5s, 1=forward 1s,2 turn right 0.5s, 3 forward 1s, 4=right 0.5s, 5 forward 1s, 6 turnleft 0.5s
bypass_mode_times = [0.5, 1.0, 0.5, 1, 0.5, 1, 0.5]
bypass_mode_iter = 0
time_waiting_for_car = 10
time_standing_still = 0

#if testing time it takes to run program
stop_after_iter = 100
sum_time = 0
iteration = 0

#in CV2 range is: H 0-180, S 0-255, V 0-255
#kiwi values: (car ==0)
#greenLower=(32,150,80) #30,x #70 (35, 150, 150)
#greenUpper=(70,255,255)
#snowfox values (car = 1)
greenLower=(45,150,100) #(36,150,150)#30,x #70 (35, 150, 150)
greenUpper=(70,255,255)

#print cv2.__version__
################################################################################
# This callback is triggered whenever there is a new distance reading coming in.
def ultraSonicRead(msg, senderStamp, timeStamps):
	#senderstamp 0 = front
	global dist_front
	global dist_back

	lock.acquire()
	if senderStamp == 0:
		dist_front = msg.distance
		#print "dist_front: ", dist_front
	elif senderStamp == 2:
		dist_back = msg.distance
		#print "dist_back: ", dist_back
        lock.release()

def infraRedRead(msg, senderStamp, timeStamps):
	#senderstamp 0 = front
	global dist_left
	global dist_right
	#print msg

	lock.acquire()
	if senderStamp == 1:
		dist_left = convertVoltToDistance(msg.voltage)
		#print "msg left: ", msg
	elif senderStamp == 3:
		dist_right = convertVoltToDistance(msg.voltage)
		#print "msg right: ", msg
        lock.release()

#crop mode minimizes the window surrounding the tracked object

# used by the crop mode which has not been tested yet
def initCrop():  
	global p1x
	global p1y
	global p2x
	global p2y
	global image_width
	global cropped_in_y
	p1x = 0
	p1y = 0
	p2x = image_width
	p2y = cropped_in_y

# used by the crop mode which has not been tested yet
def cropImage(img):
	global p1x
	global p1y
	global p2x
	global p2y
	#print img.shape
	#print " crop_img: ", p1y, " ", p2y, " ", p1x, " ", p2x
	return img[p1y:p2y, p1x:p2x]


# used by the crop mode which has not been tested yet
def setCropData(x,y,width,height):
	border_offset = 50
	global p1x
	global p1y
	global p2x
	global p2y
	global cropped_in_y
	global image_width

	if height > 0:
		p1x_t = (p1x + x) - border_offset
		p1y_t = (p1y + y) - border_offset
		p2x_t = ((p1x + x) + width) + border_offset
		p2y_t = ((p1y + y) + height) + border_offset
		#print " x:",x,"y:",y,"width:",width,"height:",height
		#print " before calc: ", p1y_t, " ", p2y_t, " ", p1x_t, " ", p2x_t
		if p1x_t < 0 :  #if object is to the left in the image then use half of the screen instead
       			p1x_t = 0
			p1y_t = 0
        	        p2x_t = 320
        	        p2y_t = cropped_in_y
		elif p2x_t > image_width : #if obejct is to the right in the picture then use the right half of the screen
       			p1x_t = 320
			p1y_t = 0
        	        p2x_t = image_width
        	        p2y_t = cropped_in_y
		elif p1y_t < 0 :  #if the object is at the top border
			p1y_t = 0
		elif p2y_t > cropped_in_y:  #the image is cropped already so only use pixels down to 320
			p2y_t = cropped_in_y
	else:
			p1x_t = 0
			p1y_t = 0
        	        p2x_t = image_width
        	        p2y_t = cropped_in_y
	p1x = p1x_t
	p1y = p1y_t
	p2x = p2x_t
	p2y = p2y_t
	#print " after calc: ", p1y, " ", p2y, " ", p1x, " ", p2x

#equalize colors for S and V in order to get correct colors in ppicture when tracking object
def hsv_equalized(image):
    global clahe
    h,s,v = cv2.split(image)
    eq_channels = []
    eq_channels.append( h )
    eq_channels.append( clahe.apply( s ))
    eq_channels.append( clahe.apply( v ))

    return cv2.merge(eq_channels)

#used to calculate correct distance for the infra red measurements
def convertVoltToDistance(voltage):
	  distance = (1.0 / (voltage / 10.13)) - 3.8
          if distance > 3.0 and distance < 40.0  :
	    distance = distance/100
            #distanceReading.distance(distance/100.0f);
            #od4.send(distanceReading, sampleTime, ID);
          else:
	    distance = -1
            #distanceReading.distance(-1);

          return distance

#just use an quardatic function instqaed of angle to object, seems to work very nice since steering will only be little in the middle of the screen
def getTurn_snowfox2(pos):
	global center_of_image
	global max_turn
	global car
	global p1x
        kt = 0.00000654
	#recalcluate the real position since the image can be cropped
	pos_in_camera = p1x + pos
	error = center_of_image - pos_in_camera
	error_squared = error*error
	turn = kt * error_squared
	if error < 0:
		turn = - turn

	#limits for the kiwi
	if turn < -0.67:
		turn = -0.67
	elif turn > 0.67:
		turn = 0.67

	if car == 1: #snowfox
		new_turn = (turn / math.pi * 180.0 / 38.0) * 10.0
		new_turn = new_turn/2
		#print "new_turn: ", new_turn, " turn: ", turn, " turn/2: ", new_turn/2, " pos: ", pos, "error: ", error
		return new_turn
	else: #kiwi
		return turn

def getSpeed_snowfox(height):
	global height_goal
	global max_speed
	global prev_height
	global car
        kp_front = 0.005 #0.01 #max_speed*10/height_goal
	kp_back = kp_front*2
	kd = 0.01 #0.01
	h = 0.5
	error = height_goal - height

	der_height = (prev_height - height)/h

	prev_height = height 
	speed = 0

	if error < 0:
 		speed = kp_front*error +kd*der_height
    		if speed > max_speed:
			speed = max_speed
		if car == 1: #snowfox
			# Scale to 0 .. 20
			new_speed = speed / 0.25 * 20.0
			print "kperror f: ",kp_front*(error), " kderror: ", kd*der_height, "error: ",error, " height: ",height
	else:
		speed = kp_back*error +kd*der_height
		if speed < max_reverse_speed:
			speed = max_reverse_speed
		if car == 1:  #snowfox
	        	# Scale to 0 .. -6
			new_speed = speed * 6.0
			print "kperror b: ",kp_back*(error), " kderror: ", kd*der_height, "error: ",error, " height: ",height
	if car == 1:
		if use_speed == 0:
			new_speed = 0
		return new_speed
	else:
		return speed

#use pd controller in order to get speed
def getSpeed_snowfox2(height):
	global distance_goal
	global max_speed
	global prev_distance
	max_speed_forward_snowfox = 20  #maxmimum 20
	max_speed_back_snowfox = -3 #maximum -6

        kp_front = 0.003
	kp_back = 0.001
	kd = 0.05 #0.01 #0.01 #0.01
	h = 1
	distance = getDistance(height)
	#print "distance: ", distance
	error = distance - distance_goal

	der_distance = (distance - prev_distance)/(h*100) #100 = 1 m
	#print "distance:",distance, "der distance: ",der_distance
	prev_distance = distance 

	if error > 0:  #have to move forward to get to the goal
 		speed = kp_front*error +kd*der_distance
    		if speed > max_speed_forward_snowfox:
			speed = max_speed_forward_snowfox
		# Scale to 0 .. 20
		#new_speed = speed / 0.25 * 20.0
		#print "kperror f: ",kp_front*(error), " kderror: ", kd*der_distance, "error: ",error, " height: ",height
	else:
		speed = kp_back*error +kd*der_distance
		if speed < max_speed_back_snowfox:
			speed = max_speed_back_snowfox
        	# Scale to 0 .. -6
		#new_speed = speed * 6.0
		#print "kperror b: ",kp_back*(error), " kderror: ", kd*der_distance, "error: ",error, " height: ",height

	if use_speed == 0:
		speed = 0
	return speed

#convert height in pixels to distance
def getDistance(height):
	k1 = 62287
	k2 = -0.973
	return k1*math.pow(height,k2)

# Create a session to send and receive messages from a running OD4Session;
# Replay mode: CID = 253
# Live mode: CID = 112
# TODO: Change to CID 112 when this program is used on Kiwi.
cid_value = 112
if car == 0:
	cid_value = 112
elif car == 1:
	cid_value = 111
session = OD4Session.OD4Session(cid=cid_value)

# Register a handler for a message; the following example is listening
# for messageID 1039 which represents opendlv.proxy.DistanceReading.
# Cf. here: https://github.com/chalmers-revere/opendlv.standard-message-set/blob/master/opendlv.odvd#L113-L115

#not needed for big car
if car == 0:
	messageIDDistanceReadingUltraSonic = 1039
	session.registerMessageCallback(messageIDDistanceReadingUltraSonic, ultraSonicRead, 	opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_DistanceReading)
	messageIDDistanceReadingInfraRed = 1037
	session.registerMessageCallback(messageIDDistanceReadingInfraRed, infraRedRead, opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_VoltageReading)
#session.registerMessageCallback(messageIDDistanceReading, onDistance, opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_DistanceReading)
#session.registerMessageCallback(messageIDDistanceReading, None, opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_DistanceReading)
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
height = 0
width = 0

################################################################################
# Main loop to process the next image frame coming in.
while True:
    #time_now = time.time()

    #diff_time = time_now - prev_time
    #prev_time = time_now
    #print "diff time: ", diff_time

    #if iteration > 0:
    #   sum_time = sum_time + diff_time
    #if iteration > stop_after_iter:
    #   print "mean: ", sum_time/stop_after_iter
    #   sys.exit(0)
    #iteration = iteration +1
    
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
    img = numpy.frombuffer(buf, numpy.uint8).reshape(image_height, image_width, 4)

    # count time it takes to process the image, uncomment code at the end of the loop
    time_now = time.time()
    ############################################################################
    # TODO: Add some image processing logic here.
#----------------
    #The bottom of the image is just wires and stuff not interesting, remove that

    crop_img = img[0:cropped_in_y, 0:image_width]

    #test to crop image in order to save time when processing the image, seems to get 5 times faster
    if use_crop_mode == 1:
	crop_img = cropImage(crop_img)

    #blur image to remove high frequency noise
    blurred = cv2.GaussianBlur(crop_img, (11, 11), 0)

    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    equ = hsv_equalized(hsv)

    # construct a mask for the color "green", then perform
    # a series of dilations and erosions to remove any small
    # blobs left in the mask
    mask = cv2.inRange(equ, greenLower, greenUpper)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    rgb_eq = cv2.cvtColor(equ, cv2.COLOR_HSV2BGR)


    _, cnts, hierarchy = cv2.findContours(mask.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # only proceed if at least one contour was found
    if len(cnts) > 0:
		# find the largest contour in the mask, then use
		# it to compute the track the object
		c = max(cnts, key=cv2.contourArea)

		#only track objects that are larger then a certain size
		#((xCirc, yCirc), radius) = cv2.minEnclosingCircle(c)
		x,y,width,height=cv2.boundingRect(c)

		#only detect object that is larger than a certain height
		if height >= Minimum_height_of_object:
			if drive_mode != 0:
				print "found car entering track mode, prev mode: ", drive_mode
				drive_mode = 0
				time_entered_mode = time.time()

			#get the edges of an enclosing rectangle
			#x,y,width,height=cv2.boundingRect(c)
			#plot an rectangle on the img
    			cv2.rectangle(crop_img,(x,y),(x+width,y+height),(0,0,255), 2)
			#get the midpoint of the contour
			M = cv2.moments(c)
			center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
			#cx = int(M['m10']/M['m00'])
    			#cy = int(M['m01']/M['m00'])
			#plot a dot in the middle of the contour			
			cv2.circle(crop_img, center, 3, (0, 0, 255), -1)
                        
			#find offset in left right direction
			turn = getTurn_snowfox2(center[0]) #center[0] == x coordinate of point

			#find offset in width goal
			speed = getSpeed_snowfox2(height)
			
			# the below code is not so good when going in a caravan since it will ruin for everyone else
  			#if car is moving backwards then shift the angle
   			#if speed < 0:
			#	turn = -turn

    		else : #lost track of object enter dead recog mode
			if drive_mode == 0:
				print "lost car, entering dead_recogning mode, prev mode: ", drive_mode
				drive_mode = 1
				time_entered_mode = time.time()
    else : #lost track of object enter dead recog mode
	if drive_mode == 0:
		print "lost car, entering dead_recogning mode, prev mode: ", drive_mode
		drive_mode = 1
		time_entered_mode = time.time()

    if view_image == 1:
	cv2.imshow("rgb_eq",crop_img)
	cv2.waitKey(10)
	#cv2.imshow("mask",mask)
	#cv2.waitKey(10)

    #check if we should enter search mode
    if drive_mode == 1:
    	if time_now - time_entered_mode > max_time_in_dead_recogning:
		print "no car found, entering search mode, prev mode: ", drive_mode
		drive_mode = 2
		time_entered_mode = time.time()
		time_entered_search_drive_mode = time_entered_mode
		speed = min_speed_back
		turn = max_turn_snowfox

    # check if we should leave search mode
    if drive_mode == 2:
    	if time_now - time_entered_mode > max_time_in_search:
		print "searched too long, stopping, prev mode: ", drive_mode
		drive_mode = 2
		time_entered_mode = time.time()
		turn = 0
		speed = 0
	else:
		print "searching...."
		if time_now - time_entered_search_drive_mode > max_time_search_driving:
			time_entered_search_drive_mode = time_now
			print "changing search mode: ", search_mode
			if search_mode == 0:   #was in front search mode, entering search back mode
				search_mode = 1
				speed = min_speed_back
				turn = 0.6
			else:
				search_mode = 0
				speed = min_speed_front
				turn = 0

    if use_crop_mode == 1:
	if drive_mode != 0:
		initCrop()
    	elif drive_mode == 0:
    		#determine where to crop image
		setCropData(x,y,width,height)


    #this was intended to be the new bypass mode, enter it if standing still to long behind a car
    # cannot be used if in a caravan and waiting
    #bypass_mode = 0 #0 turn left 0.5s, 1=forward 1s,2 turn right 0.5s, 3 forward 1s, 4=right 0.5s, 5 forward #1s, 6 turnleft 0.5s
#bypass_mode_times = [0.5, 1.0, 0.5, 1, 0.5, 1, 0.5]
#bypass_mode_iter = 0
#time_waiting_for_car = 10
#    if drive_mode == 0:
#        if speed > min_speed_back and speed < min_speed_front:
		#wait
#	if time_entered_mode > time_waiting_for_car:  #bypass car if waiting to long

#		drive_mode = 3


    #stop car if front or back if to close to an object
    if car == 0:
   	 if dist_front < dist_front_back_slow_dist:
	   if dist_front > dist_front_back_to_close:  #inside slow area
		if speed > 0:
			print "slow area front: ", dist_front, " speed: ", speed
			speed = min_speed_front
		else:  #close to collision
		   if speed > 0:
			print "close front: ", dist_front, " speed: ", speed
			speed = 0
 	   if dist_back < dist_front_back_slow_dist:
		if dist_back > dist_front_back_to_close:  #inside slow area
		   if speed < 0:
			print "slow area back: ", dist_front, " speed: ", speed
			speed = min_speed_back
		else:  #close to collision
		   if speed < 0:
			print "close back: ", dist_front, " speed: ", speed
			speed = 0

    # prevent that the car is steering into walls that are on side
    if dist_left > 0 and dist_left < dist_side_to_close and turn > 0:
	#print "To close left"
	turn = 0
    if dist_right > 0 and dist_right < dist_side_to_close and turn < 0:
	#print "To close right"
	turn = 0

    #print "dist_f: ", dist_front, "dist_b:", dist_back, " dist_l: ", dist_left, "dist_r:", dist_right
    print "speed: ", speed, " turn: " , turn, "distance: ", getDistance(height), "drive mode: ", drive_mode
 
    # if the 'q' key is pressed, stop the loop
    #if key == ord("q"):
#	break
#=====

    ############################################################################
    # Example for creating and sending a message to other microservices; can
    # be removed when not needed.
 #   angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
 #   angleReading.angle = 123.45

    # 1038 is the message ID for opendlv.proxy.AngleReading
  #  session.send(1038, angleReading.SerializeToString());

    ############################################################################
    # Steering and acceleration/decelration.
    #
    # Uncomment the following lines to steer; range: +38deg (left) .. -38deg (right).
    # Value groundSteeringRequest.groundSteering must be given in radians (DEG/180. * PI).
    if car == 0:
    	groundSteeringRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_GroundSteeringRequest()
    	groundSteeringRequest.groundSteering = turn
    	session.send(1090, groundSteeringRequest.SerializeToString());
    elif car == 1:
	actuationRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_ActuationRequest()
    	actuationRequest.steering = turn
        actuationRequest.acceleration = speed
    	actuationRequest.isValid = True
	session.send(160, actuationRequest.SerializeToString());

    # Uncomment the following lines to accelerate/decelerate; range: +0.25 (forward) .. -1.0 (backwards).
    # Be careful!
    #pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()
    #pedalPositionRequest.position = speed
    #session.send(1086, pedalPositionRequest.SerializeToString());

    # add this if checking the time it takes to run loop
    #print "diff_time inside loop: ", time.time() - time_now
    if iteration > 0:
       sum_time = sum_time + (time.time() - time_now)
       
    if iteration > stop_after_iter:
       print "mean: ", sum_time/stop_after_iter
       sys.exit(0)
    iteration = iteration +1

