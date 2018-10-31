# Tellocv tracker
Tracking code for the Tello drone. It uses opencv and tellopy to identify a ball in the scene and then send commands to the drone.
It is written in python3 and 

## Installation
You need to have opencv installed and the following python modules for the tello and cv2:
apt

```
sudo apt install sudo libopencv-dev python3-opencv
```

pip3:

```
sudo pip3 install imutils pynput
```

you need to build tellopy from source as the :
Or install from the source code.
```
git clone https://github.com/hanyazou/TelloPy
cd TelloPy
python setup.py bdist_wheel
pip install dist/tellopy-*.dev*.whl --upgrade
```

# Flight rules
- Although tellos are very safe to operate, wear safety glasses as an added precaution
- Do not fly over people
- Memorize the controls *before* taking off
- Always be ready to land the drone (backspace)
- If the program crashes restart it to regain control
- if drone is going out of control just hit it and it will turn off.

## Tello lights

- flashing blue - charging
- solid blue - charged
- flashing purple - booting up
- flashing yellow fast - wifi network set up, waiting for connection
- flashing yellow - User connected

## Recording a video
hit r to record a video it is output to <home>/Pictures
