## Processing image data with OpenCV

This C++-template demonstrates how to develop a software module to process video data (eg., image detection, etc.) to be used with Kiwi.

Prerequisites:
* [You need to install Docker for your platform](https://docs.docker.com/install/linux/docker-ce/debian/#install-docker-ce)
* [You need to install `docker-compose`](https://docs.docker.com/compose/install/#install-compose)
* You have successfully completed the "Getting Started" tutorials [here](https://github.com/chalmers-revere/2018-wasp-summer-school/tree/master/getting-started).
* You have a recording file (`.rec`) with some video frames.


## Building and testing the software module for your laptop (replay mode)

This template folder contains everything you need to compile and run a C++ software component that uses OpenCV for image processing. We are using Docker to build and run the resulting binary.

* Step 1: Assuming that you have a folder `~/recordings`, where you have at least one `.rec` file from your experiments with Kiwi. Now, you can start the h264 decoder and webapp for replaying as follows (the actual h264 decoder is built once during the first call):
```bash
docker-compose -f h264-decoder-viewer.yml up
```

* Step 2: Next, you enable access to your X11 server (GUI; necessary once per login):
```bash
xhost +
```

* Step 3: Assuming that you are located in the `image-postprocessing-opencv` folder, you can build the software module as follows:
```bash
docker build -t myapp -f Dockerfile.amd64 .
```

* Step 4: Now, you can run your software component:
```bash
docker run --rm -ti --init --net=host --ipc=host -v /tmp:/tmp -e DISPLAY=$DISPLAY myapp --cid=253 --name=img.argb --width=640 --height=480 --verbose
```

The application should start and wait for images to come in. Therefore, start a webbrowser and connect to your local webapp: [http://localhost:8081](http://localhost:8081) and open the folder view. Select one of the `.rec` files for replay. Your software component should open a new window and display the frame.

You can stop your software component by pressing `Ctrl-C`. When you are modifying the software component, repeat step 3 and step 4 after any change to your software. After a while, you might have collected a lot of unused Docker images on your machine. You can remove them by running:

```bash
for i in $(docker images|tr -s " " ";"|grep "none"|cut -f3 -d";"); do docker rmi -f $i; done
```


## Building and running the software module for Kiwi (live mode)

When you are ready to test the features and performance of your software component on Kiwi in live mode, you need to build the software component for `armhf`. Therefore, you will find a file named `Dockerfile.armhf` in this template folder that describes the necessary steps to build your software component for `armhf`.  

* Step 1: Assuming that you are located in the `image-postprocessing-opencv` folder, you can build the software module for `armhf` as follows:
```bash
docker build -t myapp.armhf -f Dockerfile.armhf .
```

* Step 2: After having successfully built the software component and packaged it into a Docker image for `armhf`, you need to transfer this Docker image from your laptop to Kiwi. Therefore, you save the Docker image to a file:
```bash
docker save myapp.armhf > myapp.armhf.tar
```

* Step 3: Next, you copy the image to Kiwi's *Raspberry Pi* using secure copy (`scp`):
```bash
scp myapp.armhf.tar debian@192.168.7.1:~
```

* Step 4: Afterwards, you log in to Kiwi's *Raspberry Pi* and load the Docker image:
```bash
ssh debian@192.168.7.1
cat myapp.armhf.tar | docker load
```

* Step 5: Finally, you can run your software component next to other microservices on Kiwi's *Raspberry Pi*:
```bash
docker run --rm -ti --init --net=host --ipc=host -v /tmp:/tmp myapp.armhf --cid=111 --name=img.argb --width=640 --height=480
```

Alternatively, you can also modify a `.yml` file from the Getting Started tutorial to include your software component:
```yml
    myapp:
        container_name: myapp
        image: myapp.armhf
        restart: on-failure
        network_mode: "host"
        ipc: "host"
        volumes:
        - /tmp:/tmp
        command: "--cid=111 --name=img.argb --width=640 --height=480"
```
