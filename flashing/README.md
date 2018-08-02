# Reinstalling Debian OS on the kiwi

This guide will provide you the steps to install Debian on the beaglebone blue and raspberry pi 3 computers on the kiwi platform. They are pre-installed on the platform already, so use this guide as a last resort for resetting the platform or installation reference.

This "Getting Started" tutorial will introduce you to Kiwi, the miniature vehicle platform from Chalmers Revere. Its hardware and software are entirely open source and you are invited to use, change, and contribute.

## Table of Contents
* [Beaglebone blue](#beaglebone-blue)
* [Raspberry pi 3](#raspberry-pi-3)

---

### Beaglebone blue

1. Download the following debian image that is custom build for beaglebone blue: https://rcn-ee.net/rootfs/bb.org/testing/2018-07-15/stretch-iot/BBBL-blank-debian-9.5-iot-armhf-2018-07-15-4gb.img.xz

2. Use a program to flash sdcard with the newly downloaded debian image. I'd recommend etcher (https://etcher.io/). Use a spare sdcard if possible, this step will wipe it clean for the debian image.

3. Put the sdcard into the beaglebone blue sdcard slot and reboot it. It will now flash the eMMC on the chip. You will see the LEDs flash in a orderly manner back and fourth. Once it's done, the LEDs should be turned off and static. Remove the sdcard and reboot.

4. Connect to the beaglebone via usb and you will see two network interfaces active. One interface will have a static IP of 192.168.6.1 and the other broadcast a dhcp server IP at 192.168.7.2. I would highly recommend to start sharing your internet connection via the interface with static ip. Ssh into the beaglebone via 192.168.7.2 and get root privilege 

* Connecting: `ssh debian@192.168.7.2`
  * Password: temppwd
* Get root privilege: `su`
  * Password: root

5. Once inside, share your internet connection and connect the beaglebone to it. If you shared it via the static interface can use `dhclient usb1`.

6. Use the installation script: https://github.com/bjornborg/bbb/blob/master/bbb/install-post.sh

* `curl -sSL https://raw.githubusercontent.com/bjornborg/bbb/master/bbb/install.sh | sh`

The installation will prompt you some options for some packages.

* For librobotcontrol: Use rc_blink
* For iptables-persistent: ipv4 yes and ipv6 yes

7. When it is done, it will prompt you a message to press enter to shutdown and then you are done!

### Raspberry pi 3


1. Download the following debian image that is custom build for raspberry pi 3: https://www.raspberrypi.org/downloads/raspbian/ 
I recommend using the lite version without any graphical interface for optimum performance.

2. Use a program to flash sdcard with the newly downloaded debian image. I'd recommend etcher (https://etcher.io/). Use a spare sdcard if possible, this step will wipe it clean for the debian image.

3. Before unmounting the sdcard after the flashing, create a file named ssh on the rootfs system. This will enable ssh functionality at boot on default. Unmount and insert the sdcard to the raspberry pi 3. Before booting up raspberry pi 3, make sure that the beaglebone blue is powered up first and connected to the rasperry pi 3 via the USB. This is to ensure the configuration is done properly.

4. Connect to the raspberry pi 3 via ethernet (share your network/internet by acting as a dhcp server alternatively connect your pc and raspberry pi 3 to a router).

5. Find the ip address of the raspberry pi 3. On linux system use nmap, e.g.

* Finding the ip: nmap 10.42.0.1/24

if your ip address 10.42.0.1

6. Connect the raspberry pi 3 via ssh

* Connecting: `ssh pi@10.42.0.33`
  * Password: raspberry
replace 10.42.0.33 with the found ip adress from previous step.

7. Get root privileges

`sudo -i`

8. Use our installation script

* Script: `curl -sSL https://raw.githubusercontent.com/bjornborg/bbb/master/rpi3/install.sh | sh`

9. Once the script is done, it will prompt you to press enter to reboot and you are done.
