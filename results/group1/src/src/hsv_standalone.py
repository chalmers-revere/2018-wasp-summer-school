# -*- coding: utf-8 -*-
"""
Created on Mon Aug 20 14:59:27 2018

@author: mayerick
"""

import cv2
import numpy as np
import os 

cap = cv2.VideoCapture(0)
cv2.namedWindow('Image')
cv2.namedWindow('Masked')

def nothing(x):
    pass

# create trackbars for color change
cv2.createTrackbar('H_low','Image',0,180,nothing)
cv2.createTrackbar('S_low','Image',0,255,nothing)
cv2.createTrackbar('V_low','Image',0,255,nothing)
cv2.createTrackbar('H_upper','Image',0,180,nothing)
cv2.createTrackbar('S_upper','Image',0,255,nothing)
cv2.createTrackbar('V_upper','Image',0,255,nothing)

load_preset = True 

if load_preset:
    if os.path.isfile('hsv_thresh.npz'):
        f = np.load('hsv_thresh.npz')
        lower_hsv = f['min_thresh']
        higher_hsv = f['max_thresh']
        
        # Set trackbars to read values
        cv2.setTrackbarPos('H_low','Image',lower_hsv[0])
        cv2.setTrackbarPos('S_low','Image',lower_hsv[1])
        cv2.setTrackbarPos('V_low','Image',lower_hsv[2])
        cv2.setTrackbarPos('H_upper','Image',higher_hsv[0])
        cv2.setTrackbarPos('S_upper','Image',higher_hsv[1])
        cv2.setTrackbarPos('V_upper','Image',higher_hsv[2])
    else:
        print('Preset files was not found! Using default values.')
        

while(True):
    # grab the frame
    ret, frame = cap.read()
    
    # get trackbar positions
    ilowH = cv2.getTrackbarPos('H_low', 'Image')
    ihighH = cv2.getTrackbarPos('H_upper', 'Image')
    ilowS = cv2.getTrackbarPos('S_low', 'Image')
    ihighS = cv2.getTrackbarPos('S_upper', 'Image')
    ilowV = cv2.getTrackbarPos('V_low', 'Image')
    ihighV = cv2.getTrackbarPos('V_upper', 'Image')


    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_hsv = np.array([ilowH, ilowS, ilowV])
    higher_hsv = np.array([ihighH, ihighS, ihighV])
    mask = cv2.inRange(hsv, lower_hsv, higher_hsv)

    frame_masked = cv2.bitwise_and(frame, frame, mask=mask)

    # Find contours 
    _, cnts, hierarchy = cv2.findContours(mask, 1, 2)
    
    # Sort contours and select the largest
    if len(cnts) > 0:
        cnts_sorted = sorted(cnts, key = cv2.contourArea, reverse = True)
        cnt = cnts_sorted[0]
        area = cv2.contourArea(cnt)
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        if hull_area > 0 :
            solidity = float(area)/hull_area
        else:
            solidity=0
            
        if  area > 100 and solidity > 0.7:
            # Fit a bounding box and plot
            x,y,w,h = cv2.boundingRect(cnt)
            cv2.rectangle(frame,(x,y),(x+w,y+h),(255,255,0),2)

    # show thresholded image
    cv2.imshow('Image', frame)
    cv2.imshow('Masked', frame_masked)
    
    k = cv2.waitKey(100)  # large wait time to remove freezing
    if k == 113 or k == 27:
        break
    elif k==ord('s'):
        np.savez('hsv_thresh.npz', min_thresh=lower_hsv, max_thresh=higher_hsv )
        print('Thresholds were saved to hsv_thresh.npz ..')
        continue 


cv2.destroyAllWindows()
