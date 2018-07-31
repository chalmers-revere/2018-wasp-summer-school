# image-postprocessing-opencv

Example repository to demonstrate how to attach to a shared memory containing
an ARGB image and displaying it using OpenCV. To display the available image, you
might need to run `xhost +` to allow accesing your X11 server.

```
docker run --rm -ti --init -e DISPLAY=$DISPLAY --ipc=host -v /tmp:/tmp YourDockerImage --cid=111 --name=video0.argb --width=640 --height=480 --verbose
```
