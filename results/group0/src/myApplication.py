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
import math
import numpy
import numpy as np
import cv2
import datetime
import atexit

# OD4Session is needed to send and receive messages
import OD4Session
# Import the OpenDLV Standard Message Set.
import opendlv_standard_message_set_v0_9_6_pb2
import collections


LGREEN = (33,  40, 160)
UGREEN = (45, 255, 240)
FONT = cv2.FONT_HERSHEY_SIMPLEX
BUFSZ = 64
MIN_AREA = 500

ANGLE_MAX = 37.5
ANGLE_DEADBAND = 1.5

pts = collections.deque(maxlen=BUFSZ)


def img_resize(img, scale=1.0):
    # Resize the frame, blur it, and convert it to the HSV color space.
    scale = 0.8
    ih,iw,_ = img.shape
    w = int(iw * scale)
    h = int(ih * scale)
    return cv2.resize(img, (w, h), interpolation = cv2.INTER_AREA)


################################################################################
# Turning on/off stuff

debug = False
longitudinal_control_enabled = True
lateral_control_enabled = True

################################################################################
# Control constants
reverse_forward_ratio = 1.75
friction_bias = 0.1

################################################################################
# Map the camera distance estimate into meters
x_values = numpy.array([-0.25, 0.2417, 0.5, 0.7333])
y_values = numpy.array([0.13, 0.28, 0.5214, 0.9355])

def interp1(x, y, xq):
    if xq < x[0]:
        yq = _interp(x[0],x[1],y[0],y[1],xq)
    elif xq > x[-1]:
        yq = _interp(x[-2],x[-1],y[-2],y[-1],xq)
    else:
        for i in range(1,len(x)):
            yq = _interp(x[i-1],x[i],y[i-1],y[i],xq)
            if xq < x[i]:
                break
    return yq

def _interp(x1, x2, y1, y2, xq):
    yq = (y2-y1)/(x2-x1)*(xq-x1) + y1
    return yq

################################################################################
# Filter the measured distance and calculate derivative.
filterK = 0.3
filterKD = 0.3
last_time = None
last_distance = -1.0
last_derivative = 0.0
filter_init = False
ultras = 2.0

def filter_input(distance, timestamp):
    global last_time, last_distance, last_derivative, filter_init

    if filter_init:
        delta_datetime = timestamp - last_time
        delta_time = create_timestamp(delta_datetime.seconds, delta_datetime.microseconds)
        filtered_distance = filterK*distance + (1-filterK)*last_distance
        if delta_time > 0.0:
            derivative = (filtered_distance-last_distance)/delta_time
            filtered_derivative = filterKD*derivative + (1-filterKD)*last_derivative
        else:
            filtered_derivative = last_derivative
        last_time = timestamp
        last_distance = filtered_distance
        last_derivative = filtered_derivative
    else:
        filter_init = True
        last_time = timestamp
        last_distance = distance
        last_derivative = 0.0

def create_timestamp(seconds, microseconds):
    return float(seconds) + float(microseconds)/1000000.0

# This callback is triggered whenever there is a new distance reading coming in.
def onDistance(msg, senderStamp, timeStamps):
    global ultras

    if debug:
        print "Received distance; senderStamp=" + str(senderStamp)
        print "sent: " + str(timeStamps[0]) + ", received: " + str(timeStamps[1]) + ", sample time stamps: " + str(timeStamps[2])
        print msg

    # Only care about forward distance.
    # US sensor seem to report a max of slightly more than 1.5 m if no target
    # is seen.
    if senderStamp == 0 and msg.distance < 1.5:
        timestamp = datetime.datetime.now()
        filter_input(msg.distance,timestamp)
        ultras = msg.distance

# Create a session to send and receive messages from a running OD4Session;
# Replay mode: CID = 253
# Live mode: CID = 112
# TODO: Change to CID 112 when this program is used on Kiwi.
if debug:
    session = OD4Session.OD4Session(cid=253)
else:
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

def p_control(p_error):
    kp = 0.5

    control = kp*p_error

    if numpy.abs(control) > 0.03:
        control = control + numpy.sign(control)*friction_bias

    return control

def pd_control(p_error, d_error):
    kp = 0.3
    kd = 0.05
    p_eps = 0.02
    d_eps = 0.03

    if p_error > -p_eps and p_error < p_eps:
        p_error = 0.0
    if d_error > -d_eps and d_error < d_eps:
        d_error = 0.0

    control = kp*p_error + kd*d_error

    if numpy.abs(control) > 0.03:
        control = control + numpy.sign(control)*friction_bias

    return control

def sm_control(p_error, d_error):
    mju = 0.13
    alpha = 0.05
    beta = 0.25

    control = mju*numpy.sign(alpha*p_error + beta*d_error) + alpha*d_error

    return control

def longitudinal_control(set_point, distance, speed):
    p_error = distance-set_point
    d_error = speed

    # control = p_control(p_error)
    # control = pd_control(p_error, d_error)
    # control = sm_control(p_error, d_error)
    control = pd_control(p_error, d_error)

    if control < 0:
        control = control*reverse_forward_ratio

    return control


def clear_controls():
    send_controls(0, 0, us=0.0, seen=False, throttle=0.0)

def send_controls(angle, control, us=0.0, seen=False, throttle=0.0):
    groundSteeringRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_GroundSteeringRequest()
    groundSteeringRequest.groundSteering = math.radians(angle)
    if lateral_control_enabled:
        if debug:
            print "Steering: %.1f" % angle
        session.send(1090, groundSteeringRequest.SerializeToString());

    pedalPositionRequest = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_PedalPositionRequest()
    pedalPositionRequest.position = us

    if longitudinal_control_enabled and (seen or us < 1.4):
        session.send(1086, pedalPositionRequest.SerializeToString());


atexit.register(clear_controls)

################################################################################
# Main loop to process the next image frame coming in.
while True:
    # Wait for next notification.
    cond.Z()
    if debug:
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

    # Resize the frame, blur it, and convert it to the HSV color space.
    scale = 0.5
    ih,iw,_ = img.shape
    # iw = int(iw * scale)
    # ih = int(ih * scale)
    # img = cv2.resize(img, (iw, ih), interpolation = cv2.INTER_AREA)

    work = img
    work = cv2.GaussianBlur(work, (11, 11), 0)
    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)

    # Filter based on our color and remove noise.
    mask = cv2.inRange(hsv, LGREEN, UGREEN)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    # Find contours in the mask.
    im2, cnts, hierarchy = cv2.findContours(mask.copy(),
                                            cv2.RETR_TREE,
                                            cv2.CHAIN_APPROX_SIMPLE)
    center = None
    seen = False
    bw,bh = (0,0)

    # Only proceed if at least one contour was found.
    if len(cnts) > 0:

	# find the largest contour in the mask, then use it to compute the
	# minimum enclosing circle and centroid
        c = max(cnts, key=cv2.contourArea)
        M = cv2.moments(c)
        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        bw,bh = rect[1]
        area = bw * bh
        ar = bw / float(bh)

        if area > MIN_AREA and (ar > 0.85 and ar < 1.15):
            cv2.drawContours(img, [box], 0, (0,0,255), 2)
            pts.appendleft(center)
            seen = True

    # Loop over the set of tracked points
    for i in range(1, len(pts)):
        if pts[i - 1] is None or pts[i] is None:
            continue

        thickness = int(np.sqrt(BUFSZ / float(i + 1)) * 2.5)
        cv2.line(img, pts[i - 1], pts[i], (0, 0, 255), thickness)

    if not seen and pts:
        pts.pop()

    # Compute Throttle and steering angles for the latest point.
    angle  = 0.0
    throttle = 0.0
    if pts:
        cx, cy = pts[0]
        a = iw/2 - cx
        b = ih/2
        sa = math.degrees(math.atan(a / float(b)))
        if sa < ANGLE_DEADBAND and sa > -ANGLE_DEADBAND:
            sa = 0.0
        angle = min(max(sa, -ANGLE_MAX), ANGLE_MAX)

        throttle = 1.0 - (float(bh) / (b / 2))
        scale = min(max(0.0, throttle), 1.0)
        nh = ih/2 + (b - b*scale)
        viz = np.array([[iw/2, ih], [cx, nh], [iw/2, nh]], np.int32)
        cv2.polylines(img, [viz], True, (255,255,255), thickness=3)

        # Map the distance estimate from camera to meters and send to filter.
        timestamp = datetime.datetime.now()
        distance = interp1(x_values, y_values, throttle)
        filter_input(distance,timestamp)

    # TODO: Disable the following two lines before running on Kiwi:
    if debug:

        # Visualize throttle and steering angle.
        rstr = "Angle: %.2f" % angle
        cv2.putText(img, rstr, (10,ih/2), FONT, 0.6, (255,255,255), 1, cv2.LINE_AA)
        rstr = "Throttle: %.2f" % throttle
        cv2.putText(img, rstr, (10,ih/2 + 20), FONT, 0.6, (255,255,255), 1, cv2.LINE_AA)

        cv2.imshow("Image", img)
        cv2.imshow("Mask", mask)
        cv2.waitKey(2)

    ############################################################################
    # Example for creating and sending a message to other microservices; can
    # be removed when not needed.
    angleReading = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AngleReading()
    angleReading.angle = angle

    # 1038 is the message ID for opendlv.proxy.AngleReading
    session.send(1038, angleReading.SerializeToString());

    ############################################################################
    # Send distance reading from camera to be able to log it better
    # Misuse of altitude reading to get distance in a unique message
    cameraDistance = opendlv_standard_message_set_v0_9_6_pb2.opendlv_proxy_AltitudeReading()
    cameraDistance.altitude = throttle
    session.send(1033, cameraDistance.SerializeToString())

    ############################################################################
    # Steering and acceleration/decelration.
    #
    # Uncomment the following lines to steer; range: +38deg (left) .. -38deg (right).
    # Value groundSteeringRequest.groundSteering must be given in radians (DEG/180. * PI).

    # Uncomment the following lines to accelerate/decelerate; range: +0.25 (forward) .. -1.0 (backwards).
    # Be careful!
    set_point = 0.4
    control = longitudinal_control(set_point, last_distance, last_derivative)
    if debug:
        print control
    if control < -0.8:
        control = -0.8
    if control > 0.2:
        control = 0.2

    send_controls(angle, control, ultras, seen, throttle)
