import cv2
import numpy as np

hsv_mask = (80, 150, 150)
threshold = 0.24
upper_mask = (int(min(hsv_mask[0]*(1+threshold), 179)),
	      int(min(hsv_mask[1]*(1+threshold), 255)),
              int(min(hsv_mask[2]*(1+threshold), 255)))

lower_mask = (int(max(hsv_mask[0]*(1-threshold), 0)),
	      int(max(hsv_mask[1]*(1-threshold), 0)),
              int(max(hsv_mask[2]*(1-threshold), 0)))


path = "test_img.jpg"
#path = "sample01.png"
img = cv2.imread(path)
img = cv2.GaussianBlur(img, (25, 25), 0)
hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
mask = cv2.inRange(hsv, lower_mask, upper_mask)
output = cv2.bitwise_and(img, img, mask=mask)
cv2.imwrite("out_mask.png", output)
ret,thresh = cv2.threshold(mask, 40, 255, 0)
im2,contours,hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
if len(contours) != 0:
    # draw in blue the contours that were founded
    cv2.drawContours(output, contours, -1, 255, 3)

    #find the biggest area
    c = max(contours, key = cv2.contourArea)

    x,y,w,h = cv2.boundingRect(c)
    # draw the book contour (in green)
    cv2.rectangle(output,(x,y),(x+w,y+h),(0,255,0),2)
    
    angle_img = output
    height, width, _ = angle_img.shape
    cv2.imwrite("out_shape.png", output)
    cv2.line(angle_img,(int(width/2.),int(height/2.)),(int((x+w)/2.),int((y+h)/2.)),(255,255,255),5)
    cv2.line(angle_img,(int(width/2.),int(height/2.)),(int(width/2.), height),(255,255,255),5)
    cv2.line(angle_img,(int(width/2.),int(height)),(int((x+w)/2.),int((y+h)/2.)),(255,255,255),5)
    cv2.imwrite("out_angle.png", output)
    

    


