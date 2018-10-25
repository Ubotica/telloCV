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
import pygame
import pygame.display
import pygame.key
import pygame.locals
import pygame.font
import os
import datetime
import av
import cv2

from tracker import Tracker
from subprocess import Popen, PIPE

def main():
    pygame.init()
    pygame.display.init()
    pygame.display.set_mode((1280, 720))
    pygame.font.init()

    global font
    font = pygame.font.SysFont("dejavusansmono", 32)

    global wid
    if 'window' in pygame.display.get_wm_info():
        wid = pygame.display.get_wm_info()['window']
    print("Tello video WID:", wid)
    tellotrack = TelloTracker()

    try:
        while 1:
            time.sleep(0.01)  # loop with pygame.event.get() is too mush tight w/o some sleep
            for e in pygame.event.get():
                tellotrack.key_event(e)


                
    except e:
        print(str(e))
    finally:
        print('Shutting down connection to drone...')
        if tellotrack.video_recorder:
            toggle_recording(drone, 1)
        tellotrack.drone.quit()
        exit(1)


class TelloTracker():



    def __init__(self):
        self.prev_flight_data = None
        self.video_player = None
        self.video_recorder = None
        self.tracking = False
        self.font = None
        self.wid = None
        self.date_fmt = '%Y-%m-%d_%H%M%S'
        self.speed = 30
        self.drone = tellopy.Tello()
        self.init_drone()
        self.hud = self.init_hud()
        self.controls = self.init_controls()


    def init_drone(self):
        print("connecting to drone")
        self.drone.log.set_level(2)
        self.drone.connect()
        self.drone.start_video()
        self.drone.subscribe(self.drone.EVENT_FLIGHT_DATA, self.flightDataHandler)
        self.drone.subscribe(self.drone.EVENT_VIDEO_FRAME, self.videoFrameHandler)
        self.drone.subscribe(self.drone.EVENT_FILE_RECEIVED, self.handleFileReceived)

    def init_controls(self):
        controls = {
        'w': 'forward',
        's': 'backward',
        'a': 'left',
        'd': 'right',
        'space': 'up',
        'left shift': 'down',
        'right shift': 'down',
        'q': 'counter_clockwise',
        'e': 'clockwise',
        # arrow keys for fast turns and altitude adjustments
        'left': lambda drone, speed: self.drone.counter_clockwise(speed*2),
        'right': lambda drone, speed: self.drone.clockwise(speed*2),
        'up': lambda drone, speed: self.drone.up(speed*2),
        'down': lambda drone, speed: self.drone.down(speed*2),
        'tab': lambda drone, speed: self.drone.takeoff(),
        'backspace': lambda drone, speed: drone.land(),
        'p': self.palm_land,
        't': self.toggle_tracking,
        'r': self.toggle_recording,
        'z': self.toggle_zoom,
        'enter': self.take_picture,
        'return': self.take_picture}
        return controls

    def init_hud(self):
        hud = [
        FlightDataDisplay('height', 'ALT %3d'),
        FlightDataDisplay('ground_speed', 'SPD %3d'),
        FlightDataDisplay('battery_percentage', 'BAT %3d%%'),
        FlightDataDisplay('wifi_strength', 'NET %3d%%'),
        FlightDataDisplay(None, 'CAM %s', update=self.flight_data_mode),
        FlightDataDisplay(None, 'TRACK %s', update=self.tracker_mode),
        FlightDataDisplay(None, '%s', colour=(255, 0, 0), update=self.flight_data_recording)]
        return hud

    def toggle_recording(self):
        if self.speed == 0:
            return

        if self.video_recorder:
            # already recording, so stop
            self.video_recorder.stdin.close()
            status_print('Video saved to %s' % self.video_recorder.video_filename)
            self.video_recorder = None
            return

        # start a new recording
        filename = '%s/Pictures/tello-%s.mp4' % (os.getenv('HOME'),
                                                 datetime.datetime.now().strftime(self.date_fmt))
        
        cmd = ['mencoder', '-', '-vc', 'x264', '-fps', '30', '-ovc', 'copy', '-of', 'lavf',
               '-lavfopts', 'format=mp4', '-o', filename]
        self.video_recorder = Popen(cmd, stdin=PIPE)
        self.video_recorder.video_filename = filename
        status_print('Recording video to %s' % filename)

    def take_picture(self):
        if self.speed == 0:
            return
        self.drone.take_picture()

    def palm_land(self):
        if self.speed == 0:
            return
        self.drone.palm_land()

    def toggle_tracking(self):
        if self.speed == 0: # handle key up event
            return
        self.tracking = not(self.tracking)
        print("tracking:", self.tracking)
        return
        
    def toggle_zoom(self):
        # In "video" mode the self.drone sends 1280x720 frames.
        # In "photo" mode it sends 2592x1936 (952x720) frames.
        # The video will always be centered in the window.
        # In photo mode, if we keep the window at 1280x720 that gives us ~160px on
        # each side for status information, which is ample.
        # Video mode is harder because then we need to abandon the 16:9 display size
        # if we want to put the HUD next to the video.
        if self.speed == 0:
            return
        self.drone.set_video_mode(not self.drone.zoom)
        pygame.display.get_surface().fill((0,0,0))
        pygame.display.flip()

    def flight_data_mode(self, *args):
        return (self.drone.zoom and "VID" or "PIC")

    def tracker_mode(self, *args):
        if self.tracking:
            return "Y"
        else:
            return "N"

    def flight_data_recording(self, *args):
        return (self.video_recorder and "REC 00:00" or "")  # TODO: duration of recording

    def update_hud(self, drone, flight_data):
        (w,h) = (158,0) # width available on side of screen in 4:3 mode
        blits = []
        for element in self.hud:
            surface = element.update(drone, flight_data)
            if surface is None:
                continue
            blits += [(surface, (0, h))]
            # w = max(w, surface.get_width())
            h += surface.get_height()
        h += 64  # add some padding
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0,0,0)) # remove for mplayer overlay mode
        for blit in blits:
            overlay.blit(*blit)
        pygame.display.get_surface().blit(overlay, (0,0))
        pygame.display.update(overlay.get_rect())

    def status_print(self, text):
        pygame.display.set_caption(text)

    def flightDataHandler(self, event, sender, data):
        text = str(data)
        if self.prev_flight_data != text:
            self.prev_flight_data = text
        self.update_hud(sender, data)

    def key_event(self, e):
        if e.type == pygame.locals.KEYDOWN:
            print('+' + pygame.key.name(e.key))
            keyname = pygame.key.name(e.key)
            if keyname == 'escape':
                self.drone.quit()
                exit(0)
            if keyname in controls:
                key_handler = controls[keyname]
                if type(key_handler) == str:
                    getattr(self.drone, key_handler)(self.speed)
                else:
                    print(key_handler)
                    key_handler(self.drone, self.speed)

        elif e.type == pygame.locals.KEYUP:
            print('-' + pygame.key.name(e.key))
            keyname = pygame.key.name(e.key)
            if keyname in controls:
                key_handler = controls[keyname]
                if type(key_handler) == str:
                    getattr(self.drone, key_handler)(0)
                else:
                    key_handler(self.drone, 0)

    def videoFrameHandler(self, event, sender, data):
        # print(len(data))
        if self.video_player is None:
            cmd = [ 'mplayer', '-fps', '35', '-really-quiet' ]
            if self.wid is not None:
                cmd = cmd + [ '-wid', str(wid) ]
            self.video_player = Popen(cmd + ['-'], stdin=PIPE)

        try:
            self.video_player.stdin.write(data)
        except IOError as err:
            status_print(str(err))
            self.video_player = None

        try:
            if self.video_recorder:
                self.video_recorder.stdin.write(data)
        except IOError as err:
            status_print(str(err))
            self.video_recorder = None

    def handleFileReceived(event, sender, data):
        global date_fmt
        # Create a file in ~/Pictures/ to receive image data from the self.drone.
        path = '%s/Pictures/tello-%s.jpeg' % (
            os.getenv('HOME'),
            datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'))
        with open(path, 'wb') as fd:
            fd.write(data)
        status_print('Saved photo to %s' % path)

class FlightDataDisplay(object):
    # previous flight data value and surface to overlay
    _value = None
    _surface = None
    # function (self.drone, data) => new value
    # default is lambda self.drone,data: getattr(data, self._key)
    _update = None
    def __init__(self, key, format, colour=(255,255,255), update=None):
        self._key = key
        self._format = format
        self._colour = colour

        if update:
            self._update = update
        else:
            self._update = lambda drone, data: getattr(data, self._key)

    def update(self, drone, data):
        new_value = self._update(drone, data)
        if self._value != new_value:
            self._value = new_value
            self._surface = font.render(self._format % (new_value,), True, self._colour)
        return self._surface

if __name__ == '__main__':
    main()
