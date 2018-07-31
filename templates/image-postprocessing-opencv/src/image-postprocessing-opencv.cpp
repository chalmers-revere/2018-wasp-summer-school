/*
 * Copyright (C) 2018  Christian Berger
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "cluon-complete.hpp"
#include "opendlv-standard-message-set.hpp"

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>

#include <cstdint>
#include <cstring>
#include <iostream>
#include <memory>

int32_t main(int32_t argc, char **argv) {
    int32_t retCode{1};
    auto commandlineArguments = cluon::getCommandlineArguments(argc, argv);
    if ( (0 == commandlineArguments.count("cid")) ||
         (0 == commandlineArguments.count("name")) ||
         (0 == commandlineArguments.count("width")) ||
         (0 == commandlineArguments.count("height")) ) {
        std::cerr << argv[0] << " attaches to a shared memory area containing an ARGB image." << std::endl;
        std::cerr << "Usage:   " << argv[0] << " --cid=<OpenDaVINCI session> --name=<name of shared memory area> [--verbose]" << std::endl;
        std::cerr << "         --cid:     CID of the OD4Session for communication purposes" << std::endl;
        std::cerr << "         --name:    name of the shared memory area to attach" << std::endl;
        std::cerr << "         --width:   width of the frame" << std::endl;
        std::cerr << "         --height:  height of the frame" << std::endl;
        std::cerr << "Example: " << argv[0] << " --cid=111 --name=video0.argb --width=640 --height=480 --verbose" << std::endl;
    }
    else {
        const std::string NAME{commandlineArguments["name"]};
        const uint32_t WIDTH{static_cast<uint32_t>(std::stoi(commandlineArguments["width"]))};
        const uint32_t HEIGHT{static_cast<uint32_t>(std::stoi(commandlineArguments["height"]))};
        const bool VERBOSE{commandlineArguments.count("verbose") != 0};

        // Attach to the shared memory.
        std::unique_ptr<cluon::SharedMemory> sharedMemory{new cluon::SharedMemory{NAME}};
        if (sharedMemory && sharedMemory->valid()) {
            std::clog << argv[0] << ": Attached to shared memory '" << sharedMemory->name() << " (" << sharedMemory->size() << " bytes)." << std::endl;

            // Create an OpenCV image header using the data in the shared memory.
            IplImage *image{nullptr};
            if (VERBOSE) {
                CvSize size;
                size.width = WIDTH;
                size.height = HEIGHT;

                image = cvCreateImageHeader(size, IPL_DEPTH_8U, 4 /* four channels: ARGB */);
                sharedMemory->lock();
                {
                    image->imageData = sharedMemory->data();
                    image->imageDataOrigin = image->imageData;
                }
                sharedMemory->unlock();
            }

            // Interface to a running OpenDaVINCI session; here, you can send and receive messages.
            cluon::OD4Session od4{static_cast<uint16_t>(std::stoi(commandlineArguments["cid"]))};
            while (od4.isRunning()) {
                // Wait for a notification of a new frame.
                sharedMemory->wait();

                // Lock the shared memory.
                sharedMemory->lock();
                {
                    // TODO: Do something with the frame.

                    // Example: Display.
                    if (VERBOSE && (nullptr != image)) {
                        // Display image.
                        cvShowImage(sharedMemory->name().c_str(), image);
                        cv::waitKey(1);
                    }

                    // Example for sending a message to other microservices:
                    // 1. Instantiate the message of interest:
                    // opendlv::proxy::PedalPositionRequest ppr;
                    // 2. Set the desired value:
                    // ppr.position(20);
                    // 3. Send the message:
                    // od4.send(ppr);
                }
                sharedMemory->unlock();
            }

            if (nullptr != image) {
                cvReleaseImageHeader(&image);
            }
        }
        retCode = 0;
    }
    return retCode;
}

