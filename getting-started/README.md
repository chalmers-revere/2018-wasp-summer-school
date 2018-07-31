## Getting Started

This "Getting Started" tutorial will introduce you to the Chalmers Revere miniature platform "Kiwi".


## Table of Contents
* [Hardware Overview](#hardware-overview)
* [Connect to Kiwi](#connect-to-kiwi)
* [Running Microservices](#running-microservices)


### Hardware Overview

The following components are installed on Kiwi:

1. BeagleBone Blue board
2. Raspberry Pi 3 mod B board
3. Battery [LiPo 7.4V 1200mAh 30C]
4. Electronic Speed Control (ESC) unit [SKYRC Cheetah 60A Brushless ESC]
5. Steering servo [Hitec Midi-Servo HS-5245MG]
6. Motor [SKYRC Cheetah Brushless ESC]
7. Ultrasonic sensors (front and rear) [Devantech SRF08]
8. Infrared sensors (left and right) [Sharp GP2Y0A41SK0F]
9. Raspberry Pi Camera Module v2

The following pictures provide an overview of the installed components on Kiwi.
![top](https://github.com/chalmers-revere/2018-wasp-summer-school/raw/master/getting-started/images/front1.png)
![bottom](https://github.com/chalmers-revere/2018-wasp-summer-school/raw/master/getting-started/images/bottom.png)

All the sensors except for the camera are connected to a small PCB board and finally to the BeagleBone Blue board.

The camera is directly connected to the Raspberry Pi board.

The two boards are connected by a USB cable, which is treated by both boards as a standard network connection.

Both boards are also wireless-ready: in particular, the Raspberry Pi has WiFi capabilities, while the BeagleBone Blue has both WiFi and Bluetooth connectivity.

### Connect to Kiwi

The "Kiwi" platform comes with Wifi enabled by default and are configured to share an Internet connection (![#f03c15](https://placehold.it/15/f03c15/000000?text=+)TODO: Check). Simply search in your Wifi settings for the access point (AP) that is stated on the sticker (![#f03c15](https://placehold.it/15/f03c15/000000?text=+)TODO: Place stickers on the car) on the car and connect to that AP. Your laptop should receive an IP address within the range `192.168.7.x/24` (![#f03c15](https://placehold.it/15/f03c15/000000?text=+)TODO: Check). Once you have such an IP address, you can `ping` the computers on Kiwi or connect via `ssh` using the following credentials (user: debian, password: ??? (![#f03c15](https://placehold.it/15/f03c15/000000?text=+)TODO: Check)):

* Connect to Raspberry Pi: `ssh debian@192.168.7.1`
* Connect to BeagleBone Blue: `ssh debian@192.168.7.2`

### Running Microservices
