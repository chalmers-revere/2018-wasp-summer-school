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

currentDistance = { "value": 0.0 }

################################################################################
# This callback is triggered whenever there is a new distance reading coming in.
def onDistance(msg, senderStamp, timeStamps):
    # print "Received distance; senderStamp=" + str(senderStamp)
    # print "sent: " + str(timeStamps[0]) + ", received: " + str(timeStamps[1]) + ", sample time stamps: " + str(timeStamps[2])
    # print msg
    if (senderStamp == 0):
        currentDistance["value"] = msg.distance


# Create a session to send and receive messages from a running OD4Session;
# Replay mode: CID = 253
# Live mode: CID = 112
# TODO: Change to CID 112 when this program is used on Kiwi.
session = OD4Session.OD4Session(cid=253)
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

cx = 320
cy = 240
wx = 319
wy = 239

# inital search parameters
H = 85
sH = 15
S = 140
sS = 50
V = 180
sV = 70

foundSquare = False
failCount = 0

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
    orig_img = numpy.frombuffer(buf, numpy.uint8).reshape(480, 640, 4)
    if (not foundSquare):
        print("(RE)CALIBRATING")
        print("Current search values:")
        print("CX: %d, CY: %d, WX: %d, WY: %d" % (cx, cy, wx, wy))
        print("H: %d, S: %d  V: %d" % (H, S, V))
        print("sH: %d, sS: %d  sV: %d" % (sH, sS, sV))
        # convert our image to hsv & filter best estimate of color
        hsv = cv2.cvtColor(orig_img, cv2.COLOR_RGB2HSV)
        lower_green = numpy.array([H-sH, S-sS, V-sV])
        upper_green = numpy.array([H+sH, S+sS, V+sV])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # apply aggressive erosion
        kernel = numpy.ones((15, 15), numpy.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        cv2.imshow("initmask", mask);
        print hsv[230:250,310:330]
        cv2.waitKey(1000);

        # find countours and bounding box
        _, contours, _ = cv2.findContours(mask.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if (len(contours) == 0):
            failCount += 1
            print("CALIBRATION FAILED NUMBER %d" % (failCount))
            cx = 320
            cy = 240
            wx = 319
            wy = 239
            sH  = min(sH + 1, 15)
            sS += 1
            sV += 1
            continue

        maxh = 0
        besti = 0
        # search for contour with maximal height that has some threshold width
        for i in range(0, len(contours)):
            cnt = contours[i]
            minx = numpy.min(cnt[:,0,0])
            maxx = numpy.max(cnt[:,0,0])
            miny = numpy.min(cnt[:,0,1])
            maxy = numpy.max(cnt[:,0,1])
            if (maxy - miny > maxh and maxx - minx > 0):
                maxh = maxy - miny
                besti = i
        
        cnt = contours[besti]
        minx = numpy.min(cnt[:,0,0])
        maxx = numpy.max(cnt[:,0,0])
        miny = numpy.min(cnt[:,0,1])
        maxy = numpy.max(cnt[:,0,1])
        h = maxy - miny
        cx = int((maxx + minx)/2)
        cy = int((maxy + miny)/2)
        wx = int((maxx - minx)*1.1/2)+20
        wy = int((maxy - miny)*1.1/2)+20
        
        

        # find color bounds within found rectangle
        hue, sat, val = hsv[miny:maxy, minx:maxx,0], hsv[miny:maxy, minx:maxx,1], hsv[miny:maxy, minx:maxx,2]
        minH = int(numpy.min(hue))
        maxH = int(numpy.max(hue))
        minS = int(numpy.min(sat))
        maxS = int(numpy.max(sat))
        minV = int(numpy.min(val))
        maxV = int(numpy.max(val))
        
        H = int((minH + maxH)/2)
        S = int((minS + maxS)/2)
        V = int((minV + maxV)/2)
        sH = int((maxH - minH)/2)+2
        sS = int((maxS - minS)/2)+10
        sV = int((maxV - minV)/2)+20     
        foundSquare = True

    # display location and color used in this round
    print("Current search values:")
    print("CX: %d, CY: %d, WX: %d, WY: %d" % (cx, cy, wx, wy))
    print("H: %d, S: %d  V: %d" % (H, S, V))
    print("sH: %d, sS: %d  sV: %d" % (sH, sS, sV))

    # crop image to location
    offsety = max(cy-wy, 0)
    offsetx = max(cx-wx, 0)
    endy = min(cy+wy, 479)
    endx = min(cx+wx, 639)
    img = orig_img[offsety:endy, offsetx:endx]

    ############################################################################
    # convert to HSV 
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    lower_green = numpy.array([H-sH, S-sS, V-sV])
    upper_green = numpy.array([H+sH, S+sS, V+sV])

    # filter for green color
    mask = cv2.inRange(hsv, lower_green, upper_green)
    cv2.imshow("Filtered mask", mask);
    # erode and dilate to get only the green post-it note
    # kernel = numpy.ones((3, 3), numpy.uint8)
    # mask = cv2.erode(mask, kernel, iterations=1)    

    # determine center of the square
    M = cv2.moments(mask)
    if (M["m00"] != 0):
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
    else:
        cX = cx - offsetx
        cY = cy - offsety
    
    # calculate height of post-it note in pixels
    # find top point of square
    miny = 0
    for y in range(cY,0,-1):
        count = 0
        for x in range(-5, 5):
            if (cX+x>= 0 and cX+x<endx-offsetx):
                if (mask[y, cX+x] == 255):
                    count += 1
        if count < 3:
            miny = y
            break

    maxy = endy - offsety
    for y in range(cY,endy-offsety):
        count = 0
        for x in range(-5, 5):
            if (cX+x>= 0 and cX+x<endx-offsetx):
                if (mask[y, cX+x] == 255):
                    count += 1
        if count < 3:
            maxy = y
            break

    minx = 0
    for x in range(cX,0,-1):
        count = 0
        for y in range(-5, 5):
            if (cY+y >= 0 and cY+y < endy-offsety):
                if (mask[cY+y, x] == 255):
                    count += 1
        if count < 3:
            minx = x
            break

    maxx = endx - offsetx
    for x in range(cX,endx-offsetx):
        count = 0
        for y in range(-5, 5):
            if (cY+y >= 0 and cY+y < endy-offsety):
                if (mask[cY+y, x] == 255):
                    count += 1
        if count < 3:
            maxx = x
            break
            
    h = (maxy - miny)
    w = (maxx - minx)
    print("Detected height: %d, width: %d" % (h, w))
    if (h > 2 and h < 400 and w > 2 and w < 400):
        wx = int(round(1.3*(w+5)/2))+5
        wy = int(round(1.3*(h+5)/2))+5
        cx = cX + offsetx
        cy = cY + offsety

        vals = hsv[mask == 255]
        hue, sat, val = vals[:,0], vals[:,1], vals[:,2]
        minH = int(numpy.min(hue))
        maxH = int(numpy.max(hue))
        minS = int(numpy.min(sat))
        maxS = int(numpy.max(sat))
        minV = int(numpy.min(val))
        maxV = int(numpy.max(val))
        
        H = int(round(numpy.mean(hue)))
        S = int(round(numpy.mean(sat)))
        V = int(round(numpy.mean(val)))
        sH = min(int(round(numpy.std(hue)*2))+5, 15)
        sS = int(round(numpy.std(sat)*2))+10
        sV = int(round(numpy.std(val)*2))+20
        
    else:
        foundSquare = False
        continue

    print("Updated search values:")
    print("CX: %d, CY: %d, WX: %d, WY: %d" % (cx, cy, wx, wy))
    print("H: %d, S: %d  V: %d" % (H, S, V))
    print("sH: %d, sS: %d  sV: %d" % (sH, sS, sV))

    h = h / 10.0 + 0.001

    # F = open("data.txt","a") 
    # F.write(str(h) + " " + str(currentDistance["value"])+ "\n")
    # F.close()

    # compare with estimated distance
    d_est = 1/(0.023743329587365*h*h + 0.170169550081314*h + 0.175207394929190)

    print("Measured distance: " + str(currentDistance["value"]))
    print("Estimate distance: " + str(d_est) + "\n")

    #convert 1D array to 3D, then convert it to YCrCb and take the first element 
    #dst = cv2.cornerHarris(numpy.float32(mask), 2, 3, 0.04)
    #cv2.imshow("corners", dst)
    cv2.imshow("mask", mask);

    # The following example is adding a red rectangle and displaying the result.
    #cv2.rectangle(img, (50, 50), (100, 100), (0,0,255), 2)

    # TODO: Disable the following two lines before running on Kiwi:
    cv2.imshow("image", img);
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
    #groundSteeringRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_GroundSteeringRequest()
    #groundSteeringRequest.groundSteering = 0
    #session.send(1090, groundSteeringRequest.SerializeToString());

    # Uncomment the following lines to accelerate/decelerate; range: +0.25 (forward) .. -1.0 (backwards).
    # Be careful!
    #pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()
    #pedalPositionRequest.position = 0
    #session.send(1086, pedalPositionRequest.SerializeToString());

