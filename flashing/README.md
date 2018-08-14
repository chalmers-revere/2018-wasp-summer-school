# Reinstalling Debian OS on the kiwi

This guide will provide you the steps to install Debian on the beaglebone blue and raspberry pi 3 computers on the kiwi platform. They are pre-installed on the platform already, so use this guide as a last resort for resetting the platform or installation reference.

In this guide, we will assume that you have internet connection on your host pc and have curl package installed in the fresh debian os.


## Table of Contents
* [Beaglebone blue](#beaglebone-blue)
* [Raspberry pi 3](#raspberry-pi-3)
* [Devantech flashing](#devantech-flashing)
* [Steering calibration](#steering-calibration)

---

### Beaglebone blue

1. Download the following debian image that is custom build for beaglebone blue: https://rcn-ee.net/rootfs/bb.org/testing/2018-07-15/stretch-iot/BBBL-blank-debian-9.5-iot-armhf-2018-07-15-4gb.img.xz

2. Use a program to flash sdcard with the newly downloaded debian image. I'd recommend etcher (https://etcher.io/). Use a spare sdcard if possible, this step will wipe it clean for the debian image.

3. Put the sdcard into the beaglebone blue sdcard slot and reboot it. It will now flash the eMMC on the chip. You will see the LEDs flash in a orderly manner back and fourth. Once it's done, the LEDs should be turned off and static. Remove the sdcard and put an empty sdcard on. Then reboot (Press the RST button once(upper left corner) and then the POW button(next to it)).

4. Connect the beaglebone to your host machine via usb or connect to its wifi hotspot (password: `BeagleBone`). Ssh into the board using the predefined target IP addresses `192.168.7.2` if you connected via usb or `192.168.8.1` if you connected to the board's wifi.

* Connecting: `ssh debian@192.168.7.2` or `ssh debian@192.168.8.1`
  * Password: temppwd

5. Once inside, with `ifconfig` or `ip a` you will see two active usb network interfaces. One interface will have a static IP of 192.168.6.2 and the other at 192.168.7.2. I would recommend to start sharing your host internet connection: once done, get root privileges and connect the beaglebone to it: so if you shared it via the usb1 interface can run `dhclient usb1`.

* Get root privileges: `su`
  * Password: root

6. Use the installation script: https://github.com/bjornborg/bbb/blob/master/bbb/install-post.sh

* `curl -sSL https://raw.githubusercontent.com/bjornborg/bbb/master/bbb/install.sh | sh`

The installation will prompt you some options for some packages.

* For librobotcontrol: Use none
* For iptables-persistent: ipv4 yes and ipv6 yes

7. When the script is done, reboot and you are done!

### Raspberry pi 3


1. Download the following debian image that is custom build for raspberry pi 3: https://www.raspberrypi.org/downloads/raspbian/ 
I recommend using the lite version without any graphical interface for optimum performance.

2. Use a program to flash sdcard with the newly downloaded debian image. I'd recommend etcher (https://etcher.io/). Use a spare sdcard if possible, this step will wipe it clean for the debian image.

3. Before unmounting the sdcard after the flashing, create a file named ssh on the boot filesystem partition. This will enable ssh functionality at boot on default. Unmount and insert the sdcard to the raspberry pi 3. BEFORE BOOTING UP raspberry pi 3, make sure that the beaglebone blue is powered up first and connected to the rasperry pi 3 via the USB. This is to ensure the configuration is done properly.

4. To power up the Raspberry Pi, you need to plug in the battery and you start the ESC. This will start the Raspberry Pi(it does not have a power up button).

5. Connect to the raspberry pi 3 via ethernet (share your network/internet by acting as a dhcp server alternatively connect your pc and raspberry pi 3 to a router).

6. Find the ip address of the raspberry pi 3. On linux system use nmap, e.g.

* Finding the ip: nmap 10.42.0.1/24

if your ip address 10.42.0.1

7. Connect the raspberry pi 3 via ssh

* Connecting: `ssh pi@10.42.0.33`
  * Password: raspberry
  
(replace 10.42.0.33 with the found ip adress from previous step.)

8. Get root privileges

`sudo -i`

9. Use our installation script

* Script: `curl -sSL https://raw.githubusercontent.com/bjornborg/bbb/master/rpi3/install.sh | sh`

The installation will prompt you some options for some packages.

* For iptables-persistent: ipv4 yes and ipv6 yes

10. Once the script is done, reboot and you are done.

11. Now the port has changed so you need to ssh to the device with

* `ssh -p 8880 pi@ipaddr`

### Devantech flashing
1. After flashing the beaglebone with our installation script, there is a devantech folder at /root/bbb/devatech inside of the beaglebone (ssh into it). Navigate to it as root(do the following).

* root: `su`
  * Password: root
* change directory: `cd /root/bbb/devantech`

2. Build the binary

* `make`

3. Navigate to the directory /root/bbb, which is the one outside.

* `cd .. (Takes you to the directory outside /bbb)`

4. Bring the service down with the following command

* `docker-compose -f bbb.yml down' (NOTE: Wait until you see an output for the services with the message "done")`

5. Navigate to the directory where you runned make

* `cd devantech`

6. Unplug the front sensor and run following command

* `./devantech_change_addr 1 0x70 0x71`

to change the back sensor on the i2c-1 bus from addr 0x70 to 0x71. When the command its executed, the led flash on the sensor should be lit up upon success. Unplug and plug the sensor again, when booting up, you should see the sensor flashing the led twice. Now plug in the front sensor again. You will also see that it flashes once

7. Now you need to bring the service up again. So you need to navigate to the outside directory again

* `cd .. (It would take you to the directory /bbb)`
* `docker-compose -f bbb.yml up -d`


### Steering calibration

1. After the installation of our software, the steering might be slightly off centered causing kiwi to drift either left or right. This can be fixed by adding a small offset value to the steering as a part of the calibration. Get root privileges inside of the beaglebone (ssh into it)

`su`
Password: root

2. Goto bbb folder
`cd /root/bbb`

3. In there, you will find a .env file containing all configuration settings for the kiwi platform regarding the motors. 

* `cat .env`

The particular setting of our interest is the OFFSETS first value. Change the value from 0.0 to 0.01 for example. Positive value on offset will steer it to left. Change the values using nano for example

* `nano .env`

4. Once changing the value reload the microservices
`docker-compose -f bbb.yml down`
`docker-compose -f bbb.yml up -d`

Redo step 3 and 4 if it still needs to reconfiguered.
