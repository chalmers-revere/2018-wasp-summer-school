# -*- coding: utf-8 -*-
"""
Created on Mon Aug 20 14:59:27 2018

@author: mayerick
"""

import cv2
import numpy as np
import os 

#this is the cascade we just made. Call what you want
cascade = cv2.CascadeClassifier('cascade.xml')

'''
img = cv2.imread("C:\\Users\\mayerick\\Desktop\\wasp-summer-school\\data\\4\\1534849458436467.png")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

detections = cascade.detectMultiScale(gray, 1.1, 5)

# add this
for (x,y,w,h) in detections:
    cv2.rectangle(img,(x,y),(x+w,y+h),(255,255,0),2)

cv2.imshow('img',img)
k = cv2.waitKey(0)
cv2.destroyAllWindows()

'''

cap = cv2.VideoCapture(0)

while (1):
    ret, img = cap.read()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    detections = cascade.detectMultiScale(gray, 1.1, 5, minSize=(50,30))
    
    # add this
    for (x,y,w,h) in detections:
        cv2.rectangle(img,(x,y),(x+w,y+h),(255,255,0),2)



    cv2.imshow('img',img)
    k = cv2.waitKey(30) & 0xff
    if k == 27:
        break

cap.release()
cv2.destroyAllWindows()
