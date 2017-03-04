#import the necessary modules
import freenect
import cv2
import numpy as np
import socket

#set up the windows to show images
cv2.namedWindow("RGB")
cv2.namedWindow("Depth")
cv2.namedWindow('Threshold')
cv2.moveWindow('RGB',5,5)
cv2.moveWindow('Depth',500,5)
cv2.moveWindow('Threshold',1000,5)

#global defines
erode_kernel = np.ones((3, 3), np.uint8)
dilate_kernel = np.ones((3, 3), np.uint8)

#address setting and socket connect
TCP_IP = '140.116.164.19'
TCP_PORT = 5001
client = socket.socket()
client.connect((TCP_IP,TCP_PORT))

#function to get mouse click and print distance
def callbackFunc(e,x,y,f,p):
    if e == cv2.EVENT_LBUTTONDOWN:
       print depth[y,x]*3
cv2.setMouseCallback("Depth", callbackFunc, None)

#function to get RGB image from kinect
def get_video():
    video = freenect.sync_get_video()[0]
    video = cv2.cvtColor(video,cv2.COLOR_RGB2BGR)
    return video

#function to filter noise with a mask
def filter_noise(depth_array, mask, masked_array, row, col):
    row_ratio = 480/row
    column_ratio = 640/col
    temp_y = 0
    for i in xrange(col):
        temp_x = 0
        for j in xrange(row):
            area = masked_array[temp_x:temp_x+row_ratio-1, temp_y:temp_y+column_ratio-1]
            mask[temp_x:temp_x+row_ratio-1, temp_y:temp_y+column_ratio-1] *= area.mean()
            depth_array[temp_x:temp_x+row_ratio-1, temp_y:temp_y+column_ratio-1] += mask[temp_x:temp_x+row_ratio-1, temp_y:temp_y+column_ratio-1]
            temp_x = temp_x + row_ratio
        temp_y = temp_y + column_ratio
    return depth_array

#function to smooth depth map by bilateral filter
def filter_smooth(depth_array):
    ret, mask = cv2.threshold(depth_array, 10, 255, cv2.THRESH_BINARY_INV)
    mask_1 = mask/255
    masked_array = depth_array + mask
    blur = filter_noise(depth_array, mask_1, masked_array, 1, 1)
    blur = cv2.bilateralFilter(blur, 5, 50, 100)
    return blur
 
#function to get depth image from kinect
def get_depth():
    depth = freenect.sync_get_depth(format=freenect.DEPTH_MM)[0]
    depth = depth/30.0
    depth = depth.astype(np.uint8)
    depth = filter_smooth(depth)
    depth[0:479, 630:639] = depth[0:479, 620:629]
    return depth

while 1:
    
    #get a frame from RGB camera
    frame = get_video()
   
    #get a frame from depth sensor
    depth = get_depth()
    depth = cv2.erode(depth, erode_kernel, 4)
    depth = cv2.dilate(depth, dilate_kernel , 4)

    #thresholding 
    _,binn = cv2.threshold(depth,20,255,cv2.THRESH_BINARY_INV)
    binn = cv2.erode(binn, erode_kernel, 4)
    binn = cv2.dilate(binn,dilate_kernel , 4)

    #find contour
    v1 = 37
    v2 = 43
    edges = cv2.Canny(binn, v1, v2)
    (contours, _) = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    #find center of mass
    '''cx=0
    cy=0
    try:
        for i in range(len(contours)):
            M = cv2.moments(contours[i])
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            cv2.circle(frame, (cx, cy), 6, (0, 255, 0), 3)
        cx = cx/len(contours)
        cy = cy/len(contours)
    except:
        pass'''
    
    #draw rectangle and show
    for i in range(len(contours)):
        if (cv2.contourArea(contours[i])>500):
                x,y,w,h = cv2.boundingRect(contours[i])         
                #cv2.rectangle(binn,(x,y),(x+w,y+h),(0,0,255),2)
                #cv2.circle(binn, (x+w/2,y+h/2), 1, (0, 255, 0), 3)

                rect = cv2.minAreaRect(contours[i])               
                box = cv2.cv.BoxPoints(rect)                    
                box = np.int0(box)
                cv2.drawContours(binn,[box],0,(0,0,255),2)

                #cv2.rectangle(frame,(x,y),(x+w,y+h),(0,0,255),2)
                cv2.drawContours(frame,[box],0,(0,0,255),2)
                
                #compute the center of the rectangle
                x_center = x + w/2
                y_center = y + h/2
                a=depth[y_center,x_center]*3
                cv2.putText(frame,"%.1fcm" % a , (x,y) , cv2.FONT_HERSHEY_SIMPLEX , 1 , (0,0,255) , 2 )   
    
    #sending images via socket
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),70]
    result,imgencode = cv2.imencode('.jpg',frame,encode_param)
    data = np.array(imgencode)
    stringData_send = data.tostring()
    client.send(str(len(stringData_send)).ljust(16))
    print len(stringData_send)  
    client.send(stringData_send)
    cv2.waitKey(10)
        
    #display RGB image
    cv2.imshow('RGB',frame)
    #display depth image
    cv2.imshow('Depth',depth)
    #display threshold image
    cv2.imshow('Threshold', binn)
 
    # quit program when 'esc' key is pressed
    k = cv2.waitKey(5) & 0xFF
    if k == 27:
        break

cv2.destroyAllWindows()
