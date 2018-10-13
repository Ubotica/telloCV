"""
A ball tracker class
Based on the tutorial:
https://www.pyimagesearch.com/2015/09/14/ball-tracking-with-opencv/

Usage:
python tracker.py --video ball_tracking_example.mp4
python ball_tracking.py
"""

# import the necessary packages
from collections import deque
from imutils.video import VideoStream
import numpy as np
import argparse
import cv2
import imutils
import time

def main():
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video",
        help="path to the (optional) video file")
    args = vars(ap.parse_args())

    # define the lower and upper boundaries of the "green"
    # ball in the HSV color space, then initialize the
    # list of tracked points
    color_lower = (29, 86, 6)
    color_upper = (64, 255, 255)
    green_lower = (50, 50, 50) 
    green_upper = (70,255,255)

    # if a video path was not supplied, grab the reference
    # to the webcam
    if not args.get("video", False):
        vs = VideoStream(src=0).start()

    # otherwise, grab a reference to the video file
    else:
        vs = cv2.VideoCapture(args["video"])

    # allow the camera or video file to warm up
    time.sleep(2.0)
    stream = args.get("video", False)
    greentracker = Tracker(vs, stream, green_lower, green_upper)

    # keep looping until no more frames
    more_frames = True
    while greentracker.next_frame:
        greentracker.track()
        greentracker.show()
        greentracker.get_frame()

    # if we are not using a video file, stop the camera video stream
    if not args.get("video", False):
        vs.stop()

    # otherwise, release the camera
    else:
        vs.release()

    # close all windows
    cv2.destroyAllWindows()

class Tracker:
    def __init__(self, vs, stream, color_lower, color_upper):
        self.vs = vs
        self.stream = stream
        self.color_lower = color_lower
        self.color_upper = color_upper
        self.next_frame = True
        self.frame = None
        self.get_frame()
        height, width, depth = self.frame.shape
        self.width = width
        self.height = height
        self.midx = int(width / 2)
        self.midy = int(height / 2)
        self.xoffset = 0
        self.yoffset = 0

    def get_frame(self):
        # grab the current frame
        frame = self.vs.read()
        # handle the frame from VideoCapture or VideoStream
        frame = frame[1] if self.stream else frame
        # if we are viewing a video and we did not grab a frame,
        # then we have reached the end of the video
        if frame is None:
            self.next_frame = False
        else:        
            frame = imutils.resize(frame, width=600)
            self.frame = frame

        return frame

    def show(self):
        cv2.arrowedLine(self.frame, (self.midx, self.midy), 
                                    (self.midx + self.xoffset, self.midy - self.yoffset),
                                    (0,0,255), 5)
        # show the frame to our screen
        cv2.imshow("Frame", self.frame)
        key = cv2.waitKey(1) & 0xFF

        # if the 'q' key is pressed, stop the loop
        if key == ord("q"):
            self.next_frame = False

    def track(self):
        # resize the frame, blur it, and convert it to the HSV
        # color space
        blurred = cv2.GaussianBlur(self.frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # construct a mask for the color then perform
        # a series of dilations and erosions to remove any small
        # blobs left in the mask
        mask = cv2.inRange(hsv, self.color_lower, self.color_upper)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # find contours in the mask and initialize the current
        # (x, y) center of the ball
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if imutils.is_cv2() else cnts[1]
        center = None

        # only proceed if at least one contour was found
        if len(cnts) > 0:
            # find the largest contour in the mask, then use
            # it to compute the minimum enclosing circle and
            # centroid
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

            # only proceed if the radius meets a minimum size
            if radius > 30:
                # draw the circle and centroid on the frame,
                # then update the list of tracked points
                cv2.circle(self.frame, (int(x), int(y)), int(radius),
                    (0, 255, 255), 2)
                cv2.circle(self.frame, center, 5, (0, 0, 255), -1)

         
                self.xoffset = int(center[0] - self.midx)
                self.yoffset = int(self.midy - center[1])
            else:
                self.xoffset = 0
                self.yoffset = 0

if __name__ == '__main__':
    main()