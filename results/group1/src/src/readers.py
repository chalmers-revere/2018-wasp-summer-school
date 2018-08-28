# -*- coding: utf-8 -*-
"""
Created on Mon Aug 20 16:48:33 2018

@author: mayerick
"""
import cv2

class ImageReader():
    def __init(self):
        pass
    
    def getFrame(self):
        raise NotImplementedError


# Read frames from Webcam
class WebCamReader(ImageReader):
    
    def __init__(self, cam_id):
        super(WebCamReader, self).__init__()
        self.cap = cv2.VideoCapture(cam_id)
        
    def getFrame(self):
            # grab the frame
            _, frame = self.cap.read()
            return frame

    def close(self):
        self.cap.release()


# Read frames from disk
class DiskReader(ImageReader):
    def __init__(self, path):
        super(DiskReader, self).__init__()
        self.path = path 