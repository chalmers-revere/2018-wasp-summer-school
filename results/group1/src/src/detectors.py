# -*- coding: utf-8 -*-
"""
Created on Mon Aug 20 14:44:45 2018

@author: mayerick
"""

import numpy as np
import cv2 
import os

class Detector:
    def __init__(self):
        pass
    def detect(self):
        raise NotImplementedError
        
class HSVDetector:

    def __init__(self, preset_path=None):
        #super(HSVDetector, self).__init__()
        
        self.lower_hsv = []
        self.higher_hsv = []
        
        
        if preset_path is not None:
            if os.path.isfile(preset_path):
                f = np.load(preset_path)
                self.lower_hsv = f['min_thresh']
                self.higher_hsv = f['max_thresh']   
            else:
                print('Preset files was not found! Quitting ..')
                raise RuntimeError
        else:
            print('Preset files must be provided.')
            raise RuntimeError
        
        
    def detect(self, frame):
        bb = None
        
        # Convert frame to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Threshold the frame
        mask = cv2.inRange(hsv, self.lower_hsv, self.higher_hsv)
        
    
        # Find contours 
        _, cnts, hierarchy = cv2.findContours(mask, 1, 2)
        
        # Sort contours and select the largest
        if len(cnts) > 0:
            cnts_sorted = sorted(cnts, key = cv2.contourArea, reverse=True)
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
                bb = [x,y,w,h]
        
        return bb

import time
import numpy as np

class LBPDetector:

    def __init__(self, preset_path=None):
       

        self.N = 5
        self.t_prev = time.time()
        
        self.xh = np.zeros((8, 1))
        self.Ph = np.eye(8)

        self.reset()
        
        self.I = np.eye(4)
        self.Z = np.zeros((4, 4))

        self.Af = lambda h: np.concatenate((np.concatenate((self.I, self.Z)), np.concatenate((self.I*h, self.I))), axis=1)   
        self.C = np.concatenate((self.I, self.Z), axis=1)

        self.Q = 1.0*np.eye(8)
        self.R = 0.1*np.eye(4)

        if preset_path is not None:
            self.cascade = cv2.CascadeClassifier(preset_path)
        else:
            print('Preset files must be provided.')
            raise RuntimeError
        
        
    def detect(self, frame):

        print "Detecting"
        bb = None
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        detections = self.cascade.detectMultiScale(gray, 1.3, 5, minSize=(100,60))
        
        t = time.time()
        h = (t - self.t_prev) / self.N

        xf = self.xh
        Pf = self.Ph
        A = self.Af(h)
        for i in range(self.N):
            xf = np.matmul(A, xf) + self.Q*h
            Pf = np.matmul(np.matmul(A, Pf), A.T) + (h**2) * self.Q

        # add this
        min_norm = 10000000
        for (x,y,w,h) in detections:
            bb_temp = np.array([x, y, w, h]).reshape((4, 1))
            dist  =  np.linalg.norm(self.xh[0:4] - bb_temp, 2)
            if dist < min_norm:
                bb  = bb_temp
                min_norm = dist


        if bb is not None:
            print "predicting"
            
            err = bb - np.matmul(self.C, xf)
            S = np.matmul(np.matmul(self.C, Pf), self.C.T) + self.R
            K = np.matmul(np.matmul(Pf, self.C.T), np.linalg.inv(S))
            
            self.xh = xf + np.matmul(K, err)
            self.Ph = np.matmul((np.eye(8) - np.matmul(K, self.C)), Pf)
            
            bb = bb.T[0]
        else:
            print "not prediction"
            self.xh = xf
            self.Ph = Pf
        
        self.t_prev = t

        return self.xh[0:4].T[0], bb

    def reset(self):
        self.xh = np.zeros((8, 1))
        self.Ph = 10*np.eye(8)

        self.xh[2,0] = 100.0
        self.xh[3,0] = 150.0
