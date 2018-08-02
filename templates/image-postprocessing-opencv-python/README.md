## Processing image data with OpenCV using Python

This Python-template demonstrates how to develop a software module to process video data (eg., image detection, etc.) to be used with Kiwi.

Prerequisites:
* [You need to install Docker for your platform](https://docs.docker.com/install/linux/docker-ce/debian/#install-docker-ce)
* [You need to install `docker-compose`](https://docs.docker.com/compose/install/#install-compose)
* You have successfully completed the "Getting Started" tutorials [here](https://github.com/chalmers-revere/2018-wasp-summer-school/tree/master/getting-started).
* You have a recording file (`.rec`) with some video frames.
* You need to install Python and OpenCV (example below is for Ubuntu 18.04 LTS):
```Bash
sudo apt-get install --no-install-recommends python-opencv
```


## Testing the software module for your laptop using replay mode

This template folder contains an example how to use Python to process data residing in a shared memory area using OpenCV for image processing.

* Step 1: Assuming that you have a folder `~/recordings`, where you have at least one `.rec` file from your experiments with Kiwi. Now, you can start the h264 decoder and webapp for replaying as follows (the actual h264 decoder is built once during the first call):
```bash
docker-compose -f h264-decoder-viewer.yml up
```

* Step 2: Next, you enable access to your X11 server (GUI; necessary once per login):
```bash
xhost +
```

Next, start a webbrowser and connect to your local webapp: [http://localhost:8081](http://localhost:8081) and open the folder view. Select one of the `.rec` files for replay.

* Step 3: Run the Pyton module from the folder `image-postprocessing-opencv-python`:
```bash
sudo python displayImageFromSharedMemory.py
```

The application should start and wait for images to come in. Your software component should open a new window and display the frame.

You can stop your software component by pressing `Ctrl-C`. When you are modifying the software component, repeat step 3 after any change to your software.
