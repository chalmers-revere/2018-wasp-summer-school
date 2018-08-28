import cv2
import numpy as np


### Input color is YUV420? ###
# Or ARGB #

rgb_mask = (140, 155, 80) # color of interest, in rgb
hsv_mask = (72, 48, 60)   # color of interest, in hsv?
hsv_mask = (84, 156, 150)   # color of interest, in hsv?
threshold = 0.26	  # allowing some deviation of color

upper_mask = (int(min(hsv_mask[0]*(1+threshold), 179)),
	      int(min(hsv_mask[1]*(1+threshold), 255)),
              int(min(hsv_mask[2]*(1+threshold), 255)))

lower_mask = (int(max(hsv_mask[0]*(1-threshold), 0)),
	      int(max(hsv_mask[1]*(1-threshold), 0)),
              int(max(hsv_mask[2]*(1-threshold), 0)))

print upper_mask
print lower_mask

path = "test_img.jpg"
img = cv2.imread(path)
hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
mask = cv2.inRange(hsv, lower_mask, upper_mask)
print hsv[200][200]
imask = mask>0
green = np.zeros_like(img, np.uint8)
green[imask] = img[imask]

cv2.imwrite("out.png", green)
