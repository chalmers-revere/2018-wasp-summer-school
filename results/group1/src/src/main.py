# -*- coding: utf-8 -*-
"""
Created on Mon Aug 20 16:40:04 2018

@author: mayerick
"""
import cv2
from readers import WebCamReader, DiskReader
from detectors import HSVDetector

debug = True
source = "Webcam"
method = 'HSVdetector'
#source = "Disk"

# Select the images reader 
if source.lower() == 'webcam':
    reader = WebCamReader(0)
elif source.lower() == 'disk':
    reader = DiskReader('.')
    
# Select the detector 
if method.lower() == 'hsvdetector':
    detector = HSVDetector(preset_path='hsv_thresh.npz')
    
if debug:
    cv2.namedWindow('Detector Output')

while(1):
    frame = reader.getFrame() 
    
    bb = detector.detect(frame)
    
    if debug:
        if bb is not None:
            x,y,w,h = bb
            cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
        
        cv2.imshow('Detector Output', frame)
    
        k = cv2.waitKey(100)  # large wait time to remove freezing
        if k == 113 or k == 27:
            break

cv2.destroyAllWindows()
reader.close()
        
        
    
    