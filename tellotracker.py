"""
tellotracker:
Allows manual operation of the drone and demo tracking mode.

Requires mplayer to record/save video.

Controls:
- tab to lift off
- WASD to move the drone
- space/shift to ascend/descent slowly
- Q/E to yaw slowly
- arrow keys to ascend, descend, or yaw quickly
- backspace to land, or P to palm-land
- enter to take a picture
- R to start recording video, R again to stop recording
  (video and photos will be saved to a timestamped file in ~/Pictures/)
- Z to toggle camera zoom state
  (zoomed-in widescreen or high FOV 4:3)
- T to toggle tracking
@author Leonie Buckley, Saksham Sinha and Jonathan Byrne
@copyright 2018 see license file for details
"""

import time
import sys
import imutils
import numpy
import tellopy
import os
import datetime
import av
import cv2

from pynput import keyboard
from tracker import Tracker
from subprocess import Popen, PIPE


def main():

    tellotrack = TelloTracker()

    for packet in tellotrack.container.demux((tellotrack.vid_stream,)):
        for frame in packet.decode():

            # convert frame to cv2 image and show
            image = cv2.cvtColor(numpy.array(
                frame.to_image()), cv2.COLOR_RGB2BGR)
            tellotrack.write_hud(image)
            if tellotrack.record:
                tellotrack.record_vid(frame)
            cv2.imshow('frame', image)
            key = cv2.waitKey(1) & 0xFF

class TelloTracker(object):

    def __init__(self):
        self.prev_flight_data = None
        self.video_player = None
        self.record = False
        self.tracking = False
        self.font = None
        self.wid = None
        self.date_fmt = '%Y-%m-%d_%H%M%S'
        self.speed = 30
        self.drone = tellopy.Tello()
        self.init_drone()
        self.init_controls()
        # container for processing the packets into frames
        self.container = av.open(self.drone.get_video_stream())
        self.vid_stream = self.container.streams.video[0]
        self.out_file = None
        self.out_stream = None
        self.out_name = None
        self.start_time = time.time()

    def init_drone(self):
        print("connecting to drone")
        # self.drone.log.set_level(2)
        self.drone.connect()
        self.drone.start_video()
        self.drone.subscribe(self.drone.EVENT_FLIGHT_DATA,
                             self.flightDataHandler)
        self.drone.subscribe(self.drone.EVENT_FILE_RECEIVED,
                             self.handleFileReceived)

    def on_press(self,keyname):
        try:
            keyname = str(keyname).strip('\'')
            print('+' + keyname)
            if keyname == 'Key.esc':
                self.drone.quit()
                exit(0)
            if keyname in self.controls:
                key_handler = self.controls[keyname]
                if type(key_handler) == str:
                    getattr(self.drone, key_handler)(self.speed)
                else:
                    key_handler(self.speed)
        except AttributeError:
            print('special key {0} pressed'.format(keyname))

    def on_release(self, keyname):
        keyname = str(keyname).strip('\'')
        print('-' + keyname)
        if keyname in self.controls:
            key_handler = self.controls[keyname]
            if type(key_handler) ==  str:
                getattr(self.drone,key_handler)(0)
            else:
                key_handler(0)

    def init_controls(self):
        self.controls = {
            'w': 'forward',
            's': 'backward',
            'a': 'left',
            'd': 'right',
            'Key.space': 'up',
            'Key.shift': 'down',
            'Key.shift_r': 'down',
            'q': 'counter_clockwise',
            'e': 'clockwise',
            'i': lambda speed: self.drone.flip_forward(),
            'k': lambda speed: self.drone.flip_back(),
            'j': lambda speed: self.drone.flip_left(),
            'l': lambda speed: self.drone.flip_right(),            
            # arrow keys for fast turns and altitude adjustments
            'Key.left': lambda speed: self.drone.counter_clockwise(speed * 2),
            'Key.right': lambda speed: self.drone.clockwise(speed * 2),
            'Key.up': lambda speed: self.drone.up(speed * 2),
            'Key.down': lambda speed: self.drone.down(speed * 2),
            'Key.tab': lambda speed: self.drone.takeoff(),
            'Key.backspace': lambda speed: self.drone.land(),
            'p': lambda speed: self.palm_land(speed),
            't': lambda speed: self.toggle_tracking(speed),
            'r': lambda speed: self.toggle_recording(speed),
            'z': lambda speed: self.toggle_zoom(speed),
            'Key.enter': lambda speed: self.take_picture(speed)
        }
        print("starting key listener")
        self.key_listener = keyboard.Listener(on_press=self.on_press,
                                              on_release=self.on_release)
        self.key_listener.start()
        # self.key_listener.join()

    def write_hud(self, frame):
        stats = self.prev_flight_data.split('|')
        stats.append("Tracking:" + str(self.tracking))
        stats.append(self.flight_data_mode())
        stats.append(self.flight_data_recording())
        for idx, stat in enumerate(stats):
            text = stat.lstrip()
            cv2.putText(frame, text, (0, idx * 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (255, 0, 0), lineType=cv2.LINE_AA)

    def toggle_recording(self, speed):
        if speed == 0:
            return
        self.record = not(self.record)
        print("Record:", self.record)

        if self.record:
            self.out_name = '%s/Pictures/tello-%s.mp4' % (os.getenv('HOME'),
                             datetime.datetime.now().strftime(self.date_fmt))
            self.out_file = av.open(self.out_name, 'w')
            #self.start_time = time.time()
            self.out_stream = self.out_file.add_stream('mpeg4', self.vid_stream.rate)
            self.out_stream.pix_fmt = 'yuv420p'
            self.out_stream.width = self.vid_stream.width
            self.out_stream.height = self.vid_stream.height

        if not self.record:
            print("Video saved to ",self.out_name)
            self.out_file.close()
            self.out_stream = None

    def record_vid(self, frame):
        """
        convert frames to packets and write to file
        """ 
        new_frame = av.VideoFrame(width=frame.width, height=frame.height, format=frame.format.name)
        for i in range(len(frame.planes)):
            new_frame.planes[i].update(frame.planes[i])
        pkt = None
        try:
            pkt = self.out_stream.encode(new_frame)
        except Exception as err:
            print("encoding failed{0}".format(err))
        if pkt is not None:
            try:
                self.out_file.mux(pkt)
            except Exception:
                print('mux failed: ' + str(pkt))


    def take_picture(self, speed):
        if speed == 0:
            return
        self.drone.take_picture()

    def palm_land(self, speed):
        if speed == 0:
            return
        self.drone.palm_land()

    def toggle_tracking(self, speed):
        if speed == 0:  # handle key up event
            return
        self.tracking = not(self.tracking)
        print("tracking:", self.tracking)
        return

    def toggle_zoom(self, speed):
        # In "video" mode the self.drone sends 1280x720 frames.
        # In "photo" mode it sends 2592x1936 (952x720) frames.
        # The video will always be centered in the window.
        # In photo mode, if we keep the window at 1280x720 that gives us ~160px on
        # each side for status information, which is ample.
        # Video mode is harder because then we need to abandon the 16:9 display size
        # if we want to put the HUD next to the video.
        if speed == 0:
            return
        self.drone.set_video_mode(not self.drone.zoom)

    def flight_data_mode(self, *args):
        return (self.drone.zoom and "VID" or "PIC")

    def flight_data_recording(self, *args):
        if self.record:
            diff = int(time.time() - self.start_time)
            mins, secs = divmod(diff, 60)
            return "REC {:02d}:{:2d}".format(mins, secs)
        else:
            return ""

    def flightDataHandler(self, event, sender, data):
        text = str(data)
        if self.prev_flight_data != text:
            self.prev_flight_data = text

    def handleFileReceived(self, event, sender, data):
        # Create a file in ~/Pictures/ to receive image data from the
        # self.drone.
        path = '%s/Pictures/tello-%s.jpeg' % (
            os.getenv('HOME'),
            datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'))
        with open(path, 'wb') as fd:
            fd.write(data)
        print('Saved photo to %s' % path)

if __name__ == '__main__':
    main()
