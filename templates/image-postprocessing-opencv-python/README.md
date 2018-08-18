## Processing image data with OpenCV and controlling Kiwi using Python

This Python-template demonstrates how to develop a software module to process video data (eg., image detection, etc.) and to control Kiwi.

Prerequisites:
* [You need to install Docker for your platform](https://docs.docker.com/install/linux/docker-ce/debian/#install-docker-ce)
* [You need to install `docker-compose`](https://docs.docker.com/compose/install/#install-compose)
* You have successfully completed the "Getting Started" tutorials [here](https://github.com/chalmers-revere/2018-wasp-summer-school/tree/master/getting-started).
* You have a recording file (`.rec`) with some video frames.
* You need to install `libcluon` (example below is for Ubuntu 18.04 LTS):
```Bash
sudo add-apt-repository ppa:chrberger/libcluon
sudo apt-get update
sudo apt-get install libcluon
```
* You need to install Python, make, protobuf, and OpenCV (example below is for Ubuntu 18.04 LTS):
```Bash
sudo apt-get install --no-install-recommends \
    build-essential \
    python-protobuf \
    python-sysv-ipc \
    python-numpy \
    python-opencv \
    protobuf-compiler
```


## Testing the software module on your laptop using replay mode

This template folder contains an example how to use Python to process data residing in a shared memory area using OpenCV for image processing.

* Step 1: Assuming that you have a folder `~/recordings`, where you have at least one `.rec` file from your experiments with Kiwi. Now, you can start the h264 decoder and webapp for replaying as follows (the actual h264 decoder is built once during the first call):
```bash
docker-compose -f h264-decoder-viewer.yml up
```

* Step 2: Clone this repository:
```bash
cd $HOME
git clone https://github.com/chalmers-revere/2018-wasp-summer-school.git
cd 2018-wasp-summer-school/templates/image-postprocessing-opencv-python
```

* Step 3: The Python script uses messages from the OpenDLV Standard Message Set. To use them with Python, just run:
```bash
make
```
This step needs to be repeated whenever you change something in the message specifications.


Next, start a webbrowser and connect to your local webapp: http://localhost:8081 and open the folder view. Select one of the `.rec` files for replay and begin the replay to fill the shared memory with some image data; you can pause the replay shortly after you saw the image in your browser.

* Step 4: Run the Pyton module from the folder `image-postprocessing-opencv-python`:
```bash
python myApplication.py
```

The application should start and wait for images to come in. Now, continue to replay your recording; the Python application should open a new window and display the frames. Furthermore, the code also display the distance readings from the sensors.

You can stop the Pythong application by pressing `Ctrl-C`. When you are modifying the Python application, repeat step 4 after any change modification.
