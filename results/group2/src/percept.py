#!/usr/bin/env python2
# encoding: utf-8
# Copyright (C) 2018 John Törnblom
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

import threading
import sysv_ipc
import numpy
import math
import cv2
import logging
import time


logger = logging.getLogger(__name__)


class Perseption(object):
    running = False
    evt_handler = None
    thread = None
    
    def __init__(self, evt_handler):
        self.evt_handler = evt_handler

    def stop(self):
        self.running = False
        self.thread.join()

    def start(self):
        assert self.running is False
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    
class CameraPerseption(Perseption):
    name = None
    
    def __init__(self, evt_handler, name='/tmp/img.argb'):
        Perseption.__init__(self, evt_handler)
        self.name = name
                
    def _run(self):
        # Obtain the keys for the shared memory and semaphores.
        keySharedMemory = sysv_ipc.ftok(self.name, 1, True)
        keySemMutex = sysv_ipc.ftok(self.name, 2, True)
        keySemCondition = sysv_ipc.ftok(self.name, 3, True)
        
        # Instantiate the SharedMemory and Semaphore objects.
        shm = sysv_ipc.SharedMemory(keySharedMemory)
        mutex = sysv_ipc.Semaphore(keySemCondition)
        cond = sysv_ipc.Semaphore(keySemCondition)

        while self.running:
            start = time.time()
            
            try:
                cond.Z(timeout=1)
            except:
                continue

            
            # with statement???
            mutex.acquire()
            shm.attach()
            buf = shm.read()
            shm.detach()
            mutex.release()

            img = numpy.frombuffer(buf, numpy.uint8).reshape(480, 640, 4)
            self.on_data(img)
            
            elapsed_time = time.time() - start
            logger.info('%2.2f Hz', 1.0 / elapsed_time)
            
    def on_data(self, argb):
	# one kind of green supposed to represent the post-it
	lower_mask = (30, 200, 150)
	upper_mask = (120, 255, 255)
	#hsv_mask = (80, 150, 150)
	# allow some deviation in color
	'''
	threshold = 0.3

	upper_mask = (int(min(hsv_mask[0]*(1+threshold), 179)),
		      int(min(hsv_mask[1]*(1+threshold), 255)),
		      int(min(hsv_mask[2]*(1+threshold), 255)))

        lower_mask = (int(max(hsv_mask[0]*(1-threshold), 0)),
		      int(max(hsv_mask[1]*(1-threshold), 0)),
		      int(max(hsv_mask[2]*(1-threshold), 0)))
	'''


	### Convert ARGB input to HSV
	img = argb
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

        # "widescreen" cropping
        hsv[360:,:] = numpy.zeros(shape=[120, 640, 3])
        #hsv[300:,:] = numpy.zeros(shape=[180, 640, 3])
        #avg_brightness = numpy.mean(hsv[:, :, 2])
        
	# apply some blurring to help edge detection
	img_blurred = cv2.GaussianBlur(hsv, (5, 5), 0)

        # finds color mask between lower green color and upper green color
	mask = cv2.inRange(hsv, lower_mask, upper_mask)
	kernel = numpy.ones((2,2), numpy.uint8)
	eroded_mask = cv2.erode(mask,kernel,iterations = 5)
	dilated_mask = cv2.dilate(mask,kernel,iterations = 5)

        # only take the pixels allowed by the mask
	dilated_img = cv2.bitwise_and(img, img, mask=dilated_mask)
	ret, thresh = cv2.threshold(dilated_mask, 40, 255, 0)
	im2, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
						    cv2.CHAIN_APPROX_NONE)

	if len(contours) == 0:
            return self.evt_handler(None, None)

	c = max(contours, key = cv2.contourArea)
	x,y,w,h = cv2.boundingRect(c)

	if w > 2*h: #width should not be larger than height in normal conditions
            return self.evt_handler(None, None)
        
        if False:
            imgshow = img
            cv2.drawContours(imgshow, contours, -1, 255, 3)
            cv2.rectangle(imgshow, (x,y), (x+w,y+h), (0,255,0), 2)
            cv2.imshow("image", imgshow);
            cv2.waitKey(2)

        # magic numbers...
	height, width, _ = img.shape
	distance = 33.3 / h

        sticker_center = x + w
        image_center = width / 2.0
	angle = -math.atan((sticker_center - image_center) / 2000.0) / (distance)

        return self.evt_handler(distance, angle)


