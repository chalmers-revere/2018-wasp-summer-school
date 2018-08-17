# Getting Started Tutorial

This "Getting Started" tutorial will introduce you to Kiwi, the miniature vehicle platform from Chalmers Revere. Its hardware and software are entirely open source and you are invited to use, change, and contribute.

## Table of Contents
* [Hardware Overview](#hardware-overview)
* [Connect to Kiwi](#connect-to-kiwi)
* [Interacting with Kiwi using Microservices](#interacting-with-kiwi-using-microservices)

---

### Hardware Overview

The following components are installed on your Kiwi:

1. BeagleBone Blue board
2. Raspberry Pi 3 mod B board
3. Battery (LiPo 7.4V 1200mAh 30C)
4. Electronic Speed Control (ESC) unit (SKYRC Cheetah 60A Brushless ESC)
5. Steering servo (Hitec Midi-Servo HS-5245MG)
6. Motor (SKYRC Cheetah Brushless ESC)
7. Ultrasonic sensors (front and rear) (Devantech SRF08)
8. Infrared sensors (left and right) (Sharp GP2Y0A41SK0F)
9. Raspberry Pi Camera Module v2

The following pictures provide an overview of the installed components on Kiwi.
![top](https://github.com/chalmers-revere/2018-wasp-summer-school/raw/master/getting-started/images/front1.png)
![bottom](https://github.com/chalmers-revere/2018-wasp-summer-school/raw/master/getting-started/images/bottom.png)

All the sensors except for the camera are connected to a small PCB board and then to the BeagleBone Blue board. The camera is directly connected to the Raspberry Pi board. The two boards are connected by a USB cable, which is treated by both boards as a standard network connection. Both boards are also wireless-ready: in particular, the Raspberry Pi has WiFi capabilities, while the BeagleBone Blue has both WiFi and Bluetooth connectivity.

---

### Connect to Kiwi

Kiwi comes with Wifi enabled by default and is configured to share an Internet connection. Simply search in your Wifi settings for the access point (AP) that is stated on the sticker on the car and connect to that AP (password: BeagleBone). Your laptop should receive an IP address within the range `192.168.8.x/24`. Once you have such an IP address, you can `ping` the computers on Kiwi or connect via `ssh` using the following credentials for beaglebone (user: debian, password: temppwd) and pi (user:pi, password: raspberry).

Kiwi's Raspberry Pi is running [Rasbian Stretch](https://www.raspberrypi.org/downloads/raspbian/) and BeagleBone Blue is running [Debian 9 (stretch)](https://debian.beagleboard.org/images/bone-debian-9.2-iot-armhf-2017-10-10-4gb.img.xz).

To ssh to the beaglebone
`ssh debian@192.168.8.1`
To ssh to the pi
`ssh -p 8880 pi@192.168.8.1`

### Update the backend on Pi
Connect to the raspberry pi and get root permissions through
`sudo -i`
then run the following
`cd ~/2018-wasp-summer-school/getting-started/`
`docker-compose -f rpi-camera-x264-viewer-kiwi.yml down`
`git pull`
`docker-compose -f rpi-camera-x264-viewer-kiwi.yml up -d`
Once it finish loading, you are done.

---

### Interacting with Kiwi using Microservices

Kiwi's software is encapsulated into separate [microservices](https://en.wikipedia.org/wiki/Microservices) that interact using UDP multicast. An overview of available microservices in use at Chalmers Revere is provided [here](https://github.com/chalmers-revere/opendlv).

#### Tutorial 1: Camera Live Stream to a Webbrowser, data recording, data replay, data export

The first test is to run microservices that stream the camera feed to your webbrowser. For this test, we need the following three microservices running on *Raspberry Pi*:

1. [opendlv-device-camera-rpi](https://github.com/chalmers-revere/opendlv-device-camera-rpi) - accessing Raspberry Pi's camera
2. [opendlv-video-x264-encoder](https://github.com/chalmers-revere/opendlv-video-x264-encoder) - converting a camera frame into an h264 frame
3. [opendlv-kiwi-view](https://github.com/chalmers-revere/opendlv-kiwi-view) - web application to visualize, record, and replay data

The first microservice is opening the camera and reading the images into two shared memory areas - one contains the frame in [I420](https://wiki.videolan.org/YUV/#I420) pixel format and the other contains the frame in ARGB pixel format. While the latter might be more convenient to be used with image detection algorithms, the former is used for h264 encoding.

The second microservice is attaching to the shared memory area that contains the I420-formatted pixels and encodes each frame into an [opendlv.proxy.ImageReading](https://github.com/chalmers-revere/opendlv.standard-message-set/blob/40f0cdb83632c3d122d2f35e028331494313330f/opendlv.odvd#L150-L155) message that contains the h264-encoded frame. This message is broadcasted to other microservices.

The third microservice is providing a web-application to visualize, record, and replay any messages that are exchanged among the running microservices.

To simplify the distribution of microservices and the description how to configure and run them, we are using Docker. The listed microservices are pre-configured [here](https://raw.githubusercontent.com/chalmers-revere/2018-wasp-summer-school/master/getting-started/rpi-camera-x264-viewer-kiwi.yml) and run already on Kiwi (![#f03c15](https://placehold.it/15/f03c15/000000?text=+)TODO: Verify this).

Now, connect your laptop's webbrowser to the *Raspberry Pi's* IP address, port 8081: [http://192.168.8.1:8081](http://192.168.8.1:8081). As a result, you should see a live stream from your Kiwi's camera and the installed sensors visualized in your webbrowser.

To record the live data, simply click on the record button that should turn red. You can stop the recording by pressing that button again. To download a recording, click on the folder button next to the record button; a new page is presented that shows the available recording files that reside on Kiwi. You can select the file you would like to download by clicking on the button labeled with `.rec`. If you want to export the recorded messages a separate `.csv`, simply click on the button with the corresponding label. To delete a recording, click on the trash bin and to start a replay, simply click on the replay button.


#### Tutorial 2: Controlling Kiwi using your webbrowser

The second test is start an additional microservice to control Kiwi with your webbrowser. For this test, we run all microservices from *Tutorial 1* and add the following microservice on *BeagleBone Blue*:

* [opendlv-device-kiwi-prugw](https://github.com/chalmers-revere/opendlv-device-kiwi-prugw) - interfacing with Kiwi's motor and servo

This microservice is listening for the messages [opendlv.proxy.PedalPositionRequest](https://github.com/chalmers-revere/opendlv.standard-message-set/blob/fb11778810a37d76d45e83e52ea054dac2e2a350/opendlv.odvd#L208-L210) and [opendlv.proxy.GroundSteeringRequest](https://github.com/chalmers-revere/opendlv.standard-message-set/blob/fb11778810a37d76d45e83e52ea054dac2e2a350/opendlv.odvd#L216-L218) to interface with Kiwi's motor and servo for acceleration/deceleration and steering.

To simplify the distribution of this microservice and the description how to configure and run it, we are using Docker. The listed microservices are pre-configured and run already on Kiwi.

Now, connect your laptop's webbrowser to the *Raspberry Pi's* IP address, port 8081: [http://192.168.8.1:8081](http://192.168.8.1:8081). You should still see a live stream from your Kiwi's camera visualized in your webbrowser. Next, enable the button right to `Joystick` to send [opendlv.proxy.PedalPositionRequest](https://github.com/chalmers-revere/opendlv.standard-message-set/blob/fb11778810a37d76d45e83e52ea054dac2e2a350/opendlv.odvd#L208-L210) and [opendlv.proxy.GroundSteeringRequest](https://github.com/chalmers-revere/opendlv.standard-message-set/blob/fb11778810a37d76d45e83e52ea054dac2e2a350/opendlv.odvd#L216-L218) to interface with Kiwi's motor and servo. Now, you can click and drag with your mouse (or pan on a smartphone/tablet) to accelerate/decelerate and steer Kiwi. If you have difficulties to enable the joystick on your smartphone, try the following link: [http://192.168.8.1:8081/joystick.html](http://192.168.8.1:8081/joystick.html).

---

_Where to go from here?_

Now, you are able to use the camera from your Kiwi, visualize, record, and replay the data, and to send steering, acceleration, and deceleration commands.

Next, you can investigate our template module that is running in C++ to process video data and to interface with the car. You find the template [here](https://github.com/chalmers-revere/2018-wasp-summer-school/tree/master/templates/image-postprocessing-opencv-cpp).

Alternatively, you can investigate our template module that is running in Python to process video data. You find the template [here](https://github.com/chalmers-revere/2018-wasp-summer-school/tree/master/templates/image-postprocessing-opencv-python).
