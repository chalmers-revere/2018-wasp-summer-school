// Copyright (C) 2018  Christian Berger
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.
controllerParams={};
window.controllerRuninng = false;
PointArrayLength = 100;
corners = [];
previousRectSize = undefined; // rect size of the latest "frame"
cycleCounter = 0; // to get average of four cycles and ignore outlier rects
cycleSetLength = 5;
previousRectSizes = [] // rect sizes of current cycle set
var g_ws;
var g_libcluon;
var g_recording = false;
var g_buttonPlayState = "play";
var g_userIsSteppingForward = false;
var g_envelopeCounter = 0;
var g_mapOfMessages = {};
var g_sendFromJoystick = false;
var g_sendFromCode = false;
var g_perception = {
    front : 0,
    rear : 0,
    left : 0,
    right : 0
};


$(document).ready(function(){
    setupUI();
});

function setupUI() {
    $('#videoFrame').attr({width:640,height:480}).css({width:'640px',height:'480px'});
    var $tableMessagesOverview = $('#table-messages-overview');

    var sensorView;

    g_libcluon = libcluon();

    function getResourceFrom(url) {
        var xmlHttp = new XMLHttpRequest();
        xmlHttp.open("GET", url, false /*asynchronous request*/);
        xmlHttp.send(null);
        return xmlHttp.responseText;
    }

    if ("WebSocket" in window) {
        const wsAddress = "192.168.1.195:8081"; //
        g_ws = new WebSocket("ws://" + wsAddress + "/", "od4");
        g_ws.binaryType = 'arraybuffer';

        g_ws.onopen = function() {
            if (IS_PLAYBACK_PAGE) {
                $("#connectionStatusSymbol").removeClass("fa fa-taxi").addClass("far fa-play-circle");
            }
            $("#connectionStatusSymbol").css("color", "#3CB371");
            $("#connectionStatusText").css("color", "#3CB371");
            $("#connectionStatusText").html("connected");

            var odvd = getResourceFrom(ODVD_FILE);
            console.log("Loaded " + g_libcluon.setMessageSpecification(odvd) + " messages from specification '" + ODVD_FILE + "'.");
        };

        g_ws.onclose = function() {
            $("#connectionStatusSymbol").css("color", "#555");
            $("#connectionStatusText").css("color", "#555");
            $("#connectionStatusText").html("disconnected");
        };

        g_ws.onmessage = function(evt) {
            // This method will pass an OpenDaVINCI container to libcluon to parse it into a JSON object using the provided message specification.
            var data = JSON.parse(g_libcluon.decodeEnvelopeToJSON(evt.data));
            g_envelopeCounter++;

            // Message overview.
            if ( (data.dataType > 0) && (data.dataType != 9 /*Ignore PlayerCommand*/) && (data.dataType != 10 /*Ignore PlayerStatus*/) ) {
                // Do book keeping of envelopes.
                var currentTimeStamp = data.sampleTimeStamp.seconds * 1000 * 1000 + data.sampleTimeStamp.microseconds;

                var date = new Date(currentTimeStamp/1000);
                var year = date.getFullYear();
                var month = "0" + (date.getMonth()+1);
                var day = "0" + date.getDate();
                var hours = date.getHours();
                var minutes = "0" + date.getMinutes();
                var seconds = "0" + date.getSeconds();

                var formattedTime = year + '-' + month.substr(-2) + '-' + day.substr(-2) + ' ' + hours + ':' + minutes.substr(-2) + ':' + seconds.substr(-2);
                $("#containerTimeStamp").html(formattedTime);
                $("#containerTimeStampUnix").html(Math.floor(currentTimeStamp/1000) + " ms");

                var informationAboutEnvelopesKey = data.dataType + "/" + data.senderStamp;
                if (!(informationAboutEnvelopesKey in g_mapOfMessages)) {
                    g_mapOfMessages[informationAboutEnvelopesKey] = { sampleTimeStamp: 0,
                                                                      envelope: {} };
                }
                var informationAboutEnvelopes = g_mapOfMessages[informationAboutEnvelopesKey];
                informationAboutEnvelopes.sampleTimeStamp = currentTimeStamp;
                informationAboutEnvelopes.envelope = data;
                g_mapOfMessages[informationAboutEnvelopesKey] = informationAboutEnvelopes;

                // Update message details.
                if ( g_userIsSteppingForward || (0 == (g_envelopeCounter % 10)) ) {
                    var $tableMessagesDetails = $('#table-messages-details');
                    $tableMessagesDetails.empty(); // empty is more explicit

                    var $row = $('<tr>').appendTo($tableMessagesDetails);
                    $('<th>').text("ID").appendTo($row);
                    $('<th>').text("senderStamp").appendTo($row);
                    $('<th>').text("message name").appendTo($row);
                    $('<th>').text("sample timestamp [µs]").appendTo($row);
                    $('<th>').text("signal(s)").appendTo($row);

                    for (var k in g_mapOfMessages) {
                        var $row = $('<tr>').appendTo($tableMessagesDetails);
                        $('<td>').text(g_mapOfMessages[k].envelope.dataType).appendTo($row);
                        $('<td>').text(g_mapOfMessages[k].envelope.senderStamp).appendTo($row);
                        $('<td>').text(Object.keys(g_mapOfMessages[k].envelope)[5]).appendTo($row);
                        $('<td>').text(g_mapOfMessages[k].sampleTimeStamp).appendTo($row);
                        var msg = g_mapOfMessages[k].envelope[Object.keys(g_mapOfMessages[k].envelope)[5]];

                        var tmp = "";
                        for (var j in msg) {
                            var v = msg[j];
                            tmp += j;
                            if ((typeof msg[j]) == 'string') {
                                if (v.length > 10) {
                                    v = " (base64) " + v.substr(0, 10) + "...";
                                }
                                else {
                                    v = window.atob(v);
                                }
                            }
                            tmp += ": " + v + "<br>";
                        }
                        $('<td>').html(tmp).appendTo($row);
                    }
                }

                if ( 0 == (g_envelopeCounter % 10)) {
                    $tableMessagesOverview.empty(); // empty is more explicit

                    for (var k in g_mapOfMessages) {
                        var $row = $('<tr>').appendTo($tableMessagesOverview);
                        var $msg = $('<td>').text(Object.keys(g_mapOfMessages[k].envelope)[5]);
                        $msg.appendTo($row);
                    }
                }
            }

            // opendlv_proxy_VoltageReading
            if (1037 == data.dataType) {
                var distance = 1.0 / (data.opendlv_proxy_VoltageReading.voltage / 10.13) - 3.8;
                distance /= 100.0;

                var sensor = 0;
                var sensorOffset = 0;
                if (0 == data.senderStamp) {
                    // IR left.
                    const IRleft = 2;
                    const IRleftOffset = 8;
                    sensor = IRleft;
                    sensorOffset = IRleftOffset;
                    g_perception.left = distance;
                }
                else if (1 == data.senderStamp) {
                    // IR right.
                    const IRright = 3;
                    const IRrightOffset = 2;
                    sensor = IRright;
                    sensorOffset = IRrightOffset;
                    g_perception.right = distance;
                }
                sensorView.chart.data.datasets[sensor].data[(sensorOffset+0)%12] = distance;
                sensorView.chart.data.datasets[sensor].data[(sensorOffset+1)%12] = distance;
                sensorView.chart.data.datasets[sensor].data[(sensorOffset+2)%12] = distance;
                sensorView.update(0);
            }

            // opendlv_proxy_DistanceReading
            if (1039 == data.dataType) {
                var distance = data.opendlv_proxy_DistanceReading.distance * 100.0;
                distance = (distance > 100.0) ? 100.0 : distance;

                var sensor = 0;
                var sensorOffset = 0;
                if (0 == data.senderStamp) {
                    // Ultrasound front.
                    const USfront = 0;
                    const USfrontOffset = 11;
                    sensor = USfront;
                    sensorOffset = USfrontOffset;
                    g_perception.front = distance;
                }
                else if (2 == data.senderStamp) {
                    // Ultrasound rear.
                    const USrear = 1;
                    const USrearOffset = 5;
                    sensor = USrear;
                    sensorOffset = USrearOffset;
                    g_perception.rear = distance;
                }
                else if (1 == data.senderStamp) {
                    // IR left.
                    const IRleft = 2;
                    const IRleftOffset = 8;
                    sensor = IRleft;
                    sensorOffset = IRleftOffset;
                    g_perception.left = distance;
                }
                else if (3 == data.senderStamp) {
                    // IR right.
                    const IRright = 3;
                    const IRrightOffset = 2;
                    sensor = IRright;
                    sensorOffset = IRrightOffset;
                    g_perception.right = distance;
                }
                sensorView.chart.data.datasets[sensor].data[(sensorOffset+0)%12] = distance;
                sensorView.chart.data.datasets[sensor].data[(sensorOffset+1)%12] = distance;
                sensorView.chart.data.datasets[sensor].data[(sensorOffset+2)%12] = distance;
                sensorView.update(0);
            }

            // opendlv_proxy_ImageReading
            if ( (1055 == data.dataType) && (0 == data.senderStamp) ) {
                // Mapping function to make wide chars to regular bytes.
                strToAB = str =>
                 new Uint8Array(str.split('')
                   .map(c => c.charCodeAt(0))).buffer;

                var FRAMEFORMAT = window.atob(data.opendlv_proxy_ImageReading.fourcc);
                if ("h264" == FRAMEFORMAT) {
                    decodeAndRenderH264('videoFrame',
                                        data.opendlv_proxy_ImageReading.width,
                                        data.opendlv_proxy_ImageReading.height,
                                        strToAB(window.atob(data.opendlv_proxy_ImageReading.data)));
                }
                if ( ("VP80" == FRAMEFORMAT) ||
                     ("VP90" == FRAMEFORMAT) ) {
                    decodeAndRenderVPX('videoFrame',
                                       data.opendlv_proxy_ImageReading.width,
                                       data.opendlv_proxy_ImageReading.height,
                                       strToAB(window.atob(data.opendlv_proxy_ImageReading.data)),
                                       FRAMEFORMAT);
                }
                return;
            }

            if (data.dataType == 10 /*PlayerStatus*/) {
                if (IS_PLAYBACK_PAGE) {
                    var total = data.cluon_data_PlayerStatus.numberOfEntries;
                    var current = data.cluon_data_PlayerStatus.currentEntryForPlayback;
                    if (total > 0) {
                      var slider = document.getElementById("playbackrange");
                      slider.value = current * 100 / total;
                    }
                    return;
                }
            }
        }
        platooningOn = false;
        // add canvas rectangle drawing support to mark car
        const canvas = document.getElementById('videoFrame');
        const context = canvas.getContext("2d");

        var canvasOffset = $("#videoFrame").offset();
        var offsetX = canvasOffset.left;
        var offsetY = canvasOffset.top;

        var isDrawing = false;
        var startX;
        var startY;
        rect = {}

        const drawRect = () => {
            context.beginPath();
            context.rect(...rect.spec);
            context.lineWidth=5;
            context.strokeStyle="#00ff00";
            context.stroke();
            context.lineWidth=1;
        }
        const handleMouseDown = e =>  {
            mouseX = parseInt(e.clientX - offsetX);
            mouseY = parseInt(e.clientY - offsetY);
            $("#downlog").html("Down: " + mouseX + " / " + mouseY);

            if (isDrawing) {
                isDrawing = false;
                const width = mouseX - startX;
                const height = mouseY - startY;
                rect.spec = [startX, startY, width, height];
                previousRectSize = [width, height];
                // define global object to specify user-defined scope:
                drawRect();
                canvas.style.cursor = "default";
            } else {
                isDrawing = true;
                startX = mouseX;
                startY = mouseY;
                canvas.style.cursor = "crosshair";
            }

        }

        $("#videoFrame").mousedown(function (e) {
            handleMouseDown(e);
        });
        // initiate platooning handler
        document.getElementById("platooning-button").addEventListener("click", function( event ) {
            platooningOn = !platooningOn;
            initiateFeatures = true;
            if(platooningOn) {
                $("#platooning-button").removeClass("fas fa-toggle-off").addClass("fas fa-toggle-on");
                $("#platooning-button").css("color", "#3CB371");
                // get canvas
                canvasWidth = canvas.width;
                canvasHeight = canvas.height;
                const width = canvasWidth;
                const height = canvasHeight;
                const image = document.getElementById('screenshot');
                window.fastThreshold = 50;
                // initiate Lucas-Kanade
                curr_img_pyr = new jsfeat.pyramid_t(3);
                prev_img_pyr = new jsfeat.pyramid_t(3);
                curr_img_pyr.allocate(width, height, jsfeat.U8_t|jsfeat.C1_t);
                prev_img_pyr.allocate(width, height, jsfeat.U8_t|jsfeat.C1_t);
                point_count = 0;
                point_status = new Uint8Array(PointArrayLength);
                prev_xy = new Float32Array(PointArrayLength*2);
                curr_xy = new Float32Array(PointArrayLength*2);
                // feature update function
                const doFindFeatures = () => {
                  tracking.Fast.THRESHOLD = window.fastThreshold;
                  context.drawImage(image, 0, 0, width, height);
                  const imageData = context.getImageData(0, 0, width, height);
                  const gray = tracking.Image.grayscale(imageData.data, width, height);
                  if (initiateFeatures == true) { // find good features to track
                    corners = tracking.Fast.findCorners(gray, width, height);
                  } else {
                    // run Lucas-Kanade step:
                    // swap flow data
                    var _pt_xy = prev_xy;
                    prev_xy = curr_xy;
                    curr_xy = _pt_xy;
                    var _pyr = prev_img_pyr;
                    prev_img_pyr = curr_img_pyr;
                    curr_img_pyr = _pyr;

                    jsfeat.imgproc.grayscale(imageData.data, width, height, curr_img_pyr.data[0]);
                    curr_img_pyr.build(curr_img_pyr.data[0], true);

                    jsfeat.optical_flow_lk.track(prev_img_pyr, curr_img_pyr, prev_xy, curr_xy, point_count, 20, 30, point_status, 0.01, 0.001);
                    prune_oflow_points(context);
                    var pointInScopeCounter = 0;
                    let pointSum = [0, 0];
                    filteredPoints = curr_xy;
                    // const initialRectSize = determineBoxSize(curr_xy);
                    for (var i = 0; i < curr_xy.length; i += 2) {
                        // don't include points that enlarge rect more than 5% per step in any direction:
                         /*let xTooFarOff = false;
                        let yTooFarOff = false;
                        if (previousRectSize) {
                            const previousRectSizeOffSet = previousRectSize * 0.01;
                            xTooFarOff =
                                curr_xy[i] < previousRectSize - previousRectSizeOffSet ||
                                curr_xy[i] > previousRectSize + previousRectSizeOffSet;
                            yTooFarOff =
                                curr_xy[i + 1] < previousRectSize - previousRectSizeOffSet ||
                                curr_xy[i + 1] > previousRectSize + previousRectSizeOffSet;
                        }
                       if (xTooFarOff || yTooFarOff) {
                            continue;
                        }*/
                        /*filteredPoints.push(curr_xy[i]);
                        filteredPoints.push(curr_xy[i + 1]);*/
                        pointSum = [pointSum[0] + curr_xy[i], pointSum[1] + curr_xy[i + 1]];
                        pointInScopeCounter++;
                    }
                    // console.log(pointSum);
                    // determine median point:
                    /* xs = []
                    ys = []*/
                    /*for (var i = 1; i < dists.length * 0.02; i += 1) {
                        const maxIndex = dists.indexOf(Math.max(...dists));
                        dists[maxIndex] = 0;
                        filteredPoints[maxIndex * 2] = centroid[0];
                        filteredPoints[maxIndex * 2 + 1] = centroid[1];
                    }*/
                    const centroid = [pointSum[0] / pointInScopeCounter, pointSum[1] / pointInScopeCounter];
                    // console.log(centroid);
                    const dists = [];
                    for (var i = 0; i < filteredPoints.length; i += 2) {
                        dists.push(Math.sqrt(Math.pow(filteredPoints[i] - centroid[0], 2) + Math.pow(filteredPoints[i+1] - centroid[1], 2)));
                    }
                    /*for (var i = 1; i < dists.length * 0.01; i += 1) {
                        const maxIndex = dists.indexOf(Math.max(...dists));
                        dists[maxIndex] = 0;
                        filteredPoints[maxIndex * 2] = centroid[0];
                        filteredPoints[maxIndex * 2 + 1] = centroid[1];
                    }*/
                    const deviationDists = dists.slice(0);
                    filteredPointsWOOffsets = filteredPoints.slice(0);
                    for (var i = 1; i < deviationDists.length * 0.3; i += 1) {
                        const maxIndex = dists.indexOf(Math.max(...deviationDists));
                        deviationDists[maxIndex] = 0;
                        filteredPointsWOOffsets[maxIndex * 2] = NaN;
                        filteredPointsWOOffsets[maxIndex * 2 + 1] = NaN;
                    }
                    const deviation = deviationDists.reduce((a, b) => a + b, 0) / deviationDists.length;
                    // console.log(deviation);
                    setControls(centroid, deviation);
                    const rectSize = determineBoxSize(filteredPoints);
                    previousRectSizes.push(rectSize);
                    context.fillStyle = '#00ff00';
                    context.fillRect(...centroid, 10, 10);
                    context.strokeStyle = '#ccc';
                    context.fillStyle = '#f00';
                    if (cycleCounter === cycleSetLength) {
                        // context.lineWidth = 5;
                        // context.strokeStyle = '#00ff00';
                        let includedRects = 0;
                        // const sumRectSizes = previousRectSizes.reduce(rectSize => {});
                        // const averageRectSize = [sumRectSizes[0] / includedRects, sumRectSizes[1] / includedRects];
                        previousRectSizes = [];
                    }
                    // const topX = centroid [0] - (rectSize[0]) / 2;
                    // const topY = centroid [1] - (rectSize[1]) / 2;
                    const topLeft = determineTopLeftCorner(filteredPoints) // ????
                    if (cycleCounter === cycleSetLength) {
                        // corners = tracking.Fast.findCorners(gray, width, height);
                    }
                    context.beginPath();
                    context.rect(...topLeft, ...rectSize);
                    context.stroke();
                    /**** draw rect without outliers ****/
                    const rectSizeWo = determineBoxSize(filteredPointsWOOffsets.filter(point => !isNaN(point)));
                    context.fillStyle = '#00ff00';
                    context.fillRect(...centroid, 10, 10);
                    context.lineWidth = 5;
                    context.strokeStyle = '#00ff00';
                    const topLeftWo = determineTopLeftCorner(filteredPointsWOOffsets.filter(point => !isNaN(point)));
                    context.beginPath();
                    context.rect(...topLeftWo, ...rectSizeWo);
                    context.stroke();
                    //**** reset line width ****/
                    context.lineWidth = 1;
                    previousRectSize = rectSize;
                    // console.log(curr_xy);
                  }
                  for (var i = 0; i < corners.length; i += 2) {
                    context.fillStyle = '#f00';
                    context.fillRect(corners[i], corners[i + 1], 3, 3);
                  }
                  // update scope (rectangle) if defined:
                  if (rect.spec) {
                    // determine centroid
                    initiateFeatures = false;
                    //let pointSum = [0, 0];
                    let pointInScopeCounter = 0;
                    for (var i = 0; i < corners.length; i += 2) {
                        // console.log(corners[i] + "," + corners[i + 1]);
                        // check if point is in rectangle (scope):
                        const isInXScope =  corners[i] > rect.spec[0] &&
                                            corners[i] < rect.spec[0] + rect.spec[2];
                        const isInYScope =  corners[i + 1] > rect.spec[1] &&
                                            corners[i + 1] < rect.spec[1] + rect.spec[3];
                        if (isInXScope && isInYScope) {
                            //pointSum = [pointSum[0] + corners[i], pointSum[1] + corners[i + 1]];
                            // context.fillStyle = '#CCC';
                            // context.fillRect(corners[i], corners[i + 1], 3, 3);
                            pointInScopeCounter++;
                            curr_xy[point_count<<1] = corners[i];
                            curr_xy[(point_count<<1)+1] = corners[i + 1];
                            point_count++;
                        }

                    }
                    for (var i = 0; i < filteredPoints.length; i += 2) {
                        if (isNaN(filteredPointsWOOffsets[i])) {
                            context.fillStyle = '#ccc';
                        } else {
                            context.fillStyle = '#0000ff';
                        }
                        
                        context.fillRect(filteredPoints[i], filteredPoints[i + 1], 3, 3);
                    }
                    cycleCounter === cycleSetLength? cycleCounter = 0 : cycleCounter++;
                  }
                };
                featureFinder = setInterval(doFindFeatures, 50);
                // var gui = new dat.GUI();
                // gui.add(window, 'fastThreshold', 0, 100).onChange(doFindFeatures);
            } else {
                $("#platooning-button").removeClass("fas fa-toggle-on").addClass("fas fa-toggle-off");
                $("#platooning-button").css("color", "#555");
                clearInterval(featureFinder);
            }
        });
    }
    else {
        console.log("Error: websockets not supported by your browser.");
    }

    if (IS_PLAYBACK_PAGE) {
        var slider = document.getElementById("playbackrange");
        slider.addEventListener("change", function() {
            remotePlayerJSON = "{\"command\":3,\"seekTo\":" + (this.value/100) + "}";
            console.log(remotePlayerJSON);

            var output = g_libcluon.encodeEnvelopeFromJSONWithoutTimeStamps(remotePlayerJSON, 9 /* message identifier */, 0  /* sender stamp */);

//                strToAB = str =>
//                  new Uint8Array(str.split('')
//                    .map(c => c.charCodeAt(0))).buffer;

//     Instead of sending the raw bytes, we encapsulate them into a JSON object.
//                ws.send(strToAB(output), { binary: true });

            var commandJSON = "{\"remoteplayback\":" + "\"" + window.btoa(output) + "\"" + "}";
            g_ws.send(commandJSON);
        });
    }


    sensorView = new Chart(document.getElementById("sensorView"), {
        type: 'radar',
        data: {
            labels: ['0', '30', '60', '90', '120', '150', '180', '210', '240', '270', '300', '330'],
            datasets: [
                {
                    label: "US front",
                    borderColor: "#3498DB",
                    data: [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                }, 
                {
                    label: "US rear",
                    borderColor: "#00BFFF",
                    data: [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
                }, 
                {
                    label: "IR left",
                    borderColor: "#FF8000",
                    data: [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0],
                }, 
                {
                    label: "IR right",
                    borderColor: "#FF0000",
                    data: [0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
                }, 
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scale: {
                ticks: {
                    beginAtZero: true,
                    max: 100
                }
            },
            title: {
                display: true,
                text: 'Sensor Bird\'s Eye View'
            }
        }
    });

    ////////////////////////////////////////////////////////////////////////////
    // Joystick.
    var joystick = new VirtualJoystick({
        container: document.getElementById('center-view'),
        mouseSupport: true,
        strokeStyle: '#3498DB',
        limitStickTravel: true,
    });

    function updateFromJoystick() {
        var envPedalPositionRequest;
        var envGroundSteeringRequest;
        var envActuationRequest;

        // Values for Kiwi.
        var minSteering = 0; // Number(document.getElementById("minSteering").value)
        var maxSteering = 38; // Number(document.getElementById("maxSteering").value)
        var maxAcceleration = 25; // Number(document.getElementById("maxAcceleration").value)
        var maxDeceleration = 100; // Number(document.getElementById("maxDeceleration").value)

        var steering = 0;
        var gasPedalPosition = 0;
        var brakePedalPosition = 0;

        // Support for PedalPositionRequest & GroundSteeringRequest.
        {
            var pedalPosition = Math.floor(((-1 * joystick.deltaY())/100.0)*100.0)/100.0;

            gasPedalPosition = Math.floor(((pedalPosition > 0) ? (pedalPosition*maxAcceleration) : 0))/100.0;
            brakePedalPosition = Math.floor(((pedalPosition < 0) ? (pedalPosition*maxDeceleration) : 0))/100.0;

            var pedalPositionRequest = "{\"position\":" + (gasPedalPosition > 0 ? gasPedalPosition : brakePedalPosition) + "}";
            envPedalPositionRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(pedalPositionRequest, 1086 /* message identifier */, 0 /* sender stamp */);


            steering = Math.floor((-1 * (joystick.deltaX()/100.0) * maxSteering * Math.PI / 180.0)*100.0)/100.0;
            var groundSteeringRequest = "{\"groundSteering\":" + steering + "}";
            envGroundSteeringRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(groundSteeringRequest, 1090 /* message identifier */, 0 /* sender stamp */);
        }

        // Disable support for legacy ActuationRequest.
        {
            var actuationRequest = "{\"acceleration\":0,\"steering\":0,\"isValid\":false}";
            envActuationRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(actuationRequest, 160 /* message identifier */, 0 /* sender stamp */);

//            strToAB = str =>
//              new Uint8Array(str.split('')
//                .map(c => c.charCodeAt(0))).buffer;

// Instead of sending the raw bytes, we encapsulate them into a JSON object.
//            ws.send(strToAB(output), { binary: true });
        }

        var actuationCommands = "{\"virtualjoystick\":" +
                                    "{" +
                                        "\"pedalPositionRequest\":" + "\"" + window.btoa(envPedalPositionRequest) + "\"," +
                                        "\"groundSteeringRequest\":" + "\"" + window.btoa(envGroundSteeringRequest) + "\"," +
                                        "\"actuationRequest\":" + "\"" + window.btoa(envActuationRequest) + "\"" +
                                    "}" +
                                "}";

        if (g_sendFromJoystick) {
            g_ws.send(actuationCommands);

            $("#steering").html(steering);
            $("#motor").html((gasPedalPosition > 0 ? gasPedalPosition : brakePedalPosition));
        }
    }

    ////////////////////////////////////////////////////////////////////////////
    function updateFromCode() {
        const perception = g_perception;

        var actuation = { motor : 0,
                          steering : 0
        };

        // Run user's code.
        var editor = ace.edit("editor");
        var code = editor.getValue();
        eval(code);

        var envPedalPositionRequest;
        var envGroundSteeringRequest;
        var envActuationRequest;

        // Values for Kiwi.
        var minSteering = 0; // Number(document.getElementById("minSteering").value)
        var maxSteering = 38; // Number(document.getElementById("maxSteering").value)
        var maxAcceleration = 25; // Number(document.getElementById("maxAcceleration").value)
        var maxDeceleration = 100; // Number(document.getElementById("maxDeceleration").value)

        var steering = 0;
        var gasPedalPosition = 0;
        var brakePedalPosition = 0;

        // Support for PedalPositionRequest & GroundSteeringRequest.
        {
            gasPedalPosition = Math.floor(Math.min(actuation.motor, maxAcceleration/100.0)*100.0)/100.0;
            brakePedalPosition = Math.floor(Math.max(actuation.motor, maxAcceleration/-100.0)*100.0)/100.0;

            var pedalPositionRequest = "{\"position\":" + (actuation.motor > 0 ? gasPedalPosition : brakePedalPosition) + "}";
            envPedalPositionRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(pedalPositionRequest, 1086 /* message identifier */, 0 /* sender stamp */);


            steering = actuation.steering;
            if (steering < -maxSteering*Math.PI/180.0) {
                steering = -maxSteering*Math.PI/180.0;
            }
            else if (steering > maxSteering*Math.PI/180.0) {
                steering = maxSteering*Math.PI/180.0;
            }
            steering = Math.floor(steering*100.0)/100.0;

            var groundSteeringRequest = "{\"groundSteering\":" + steering + "}";
            envGroundSteeringRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(groundSteeringRequest, 1090 /* message identifier */, 0 /* sender stamp */);
        }

        // Disable support for legacy ActuationRequest.
        {
            var actuationRequest = "{\"acceleration\":0,\"steering\":0,\"isValid\":false}";
            envActuationRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(actuationRequest, 160 /* message identifier */, 0 /* sender stamp */);

//            strToAB = str =>
//              new Uint8Array(str.split('')
//                .map(c => c.charCodeAt(0))).buffer;

// Instead of sending the raw bytes, we encapsulate them into a JSON object.
//            ws.send(strToAB(output), { binary: true });
        }

        var actuationCommands = "{\"virtualjoystick\":" +
                                    "{" +
                                        "\"pedalPositionRequest\":" + "\"" + window.btoa(envPedalPositionRequest) + "\"," +
                                        "\"groundSteeringRequest\":" + "\"" + window.btoa(envGroundSteeringRequest) + "\"," +
                                        "\"actuationRequest\":" + "\"" + window.btoa(envActuationRequest) + "\"" +
                                    "}" +
                                "}";

        if (g_sendFromCode) {
            g_ws.send(actuationCommands);

            $("#steering").html(steering);
            $("#motor").html((gasPedalPosition > 0 ? gasPedalPosition : brakePedalPosition));
        }
    }

    ////////////////////////////////////////////////////////////////////////////
    $('body').on('click', 'button#record', function() {
        g_recording = !g_recording;
        if (g_recording) {
            $('button#record').css('color', '#D00');
            g_ws.send("{ \"record\": true }", { binary: false });
        }
        else {
            $('button#record').css('color', '#555');
            g_ws.send("{ \"record\": false }", { binary: false });
        }
    });

    ////////////////////////////////////////////////////////////////////////////
    setInterval(function() {
        updateFromJoystick();
        updateFromCode();
    }, 1/10 /* 10Hz */ * 1000);

    ////////////////////////////////////////////////////////////////////////////
    window.addEventListener("beforeunload", function (e) {
        if (IS_LIVE_PAGE) {
            var confirmationMessage = "Recording is ongoing that will be canceled when leaving this page.";
            if (g_recording) {
                (e || window.event).returnValue = confirmationMessage; //Gecko + IE
                return confirmationMessage;                            //Webkit, Safari, Chrome
            }
        }
        if (IS_PLAYBACK_PAGE) {
            fetch('/endreplay', { method: 'post',
                                headers: {
                                    'Accept': 'application/json, text/plain, */*',
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({endReplay: true})
                               }
            )
            .then(function(response) {
                if (response.ok) {
                    return;
                }
                throw new Error('Request failed.');
                })
            .catch(function(error) {
                console.log(error);
            });
        }
    });
}

////////////////////////////////////////////////////////////////////////////////

function updateSendingButtons() {
    if (g_sendFromJoystick) {
        $("#enableSendingJoyStick").removeClass("fas fa-toggle-off").addClass("fas fa-toggle-on");
        $("#enableSendingJoyStick").css("color", "#3CB371");
    }
    else {
        $("#enableSendingJoyStick").removeClass("fas fa-toggle-on").addClass("fas fa-toggle-off");
        $("#enableSendingJoyStick").css("color", "#555");
    }

    if (g_sendFromCode) {
        $("#enableSendingCode").removeClass("fas fa-toggle-off").addClass("fas fa-toggle-on");
        $("#enableSendingCode").css("color", "#3CB371");
    }
    else {
        $("#enableSendingCode").removeClass("fas fa-toggle-on").addClass("fas fa-toggle-off");
        $("#enableSendingCode").css("color", "#555");
    }

    // Stop Kiwi.
    if (!g_sendFromJoystick && !g_sendFromCode) {
        var groundSteeringRequest = "{\"groundSteering\":0}";
        var envGroundSteeringRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(groundSteeringRequest, 1090 /* message identifier */, 0 /* sender stamp */);

        var pedalPositionRequest = "{\"position\":0}";
        var envPedalPositionRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(pedalPositionRequest, 1086 /* message identifier */, 0 /* sender stamp */);

        var actuationCommands = "{\"virtualjoystick\":" +
                                    "{" +
                                        "\"pedalPositionRequest\":" + "\"" + window.btoa(envPedalPositionRequest) + "\"," +
                                        "\"groundSteeringRequest\":" + "\"" + window.btoa(envGroundSteeringRequest) + "\"" +
                                    "}" +
                                "}";
        g_ws.send(actuationCommands);
    }
}

function enableSendingJoystickToggled() {
    g_sendFromJoystick = !g_sendFromJoystick;

    if (g_sendFromJoystick) {
        g_sendFromCode = false;
    }

    updateSendingButtons();
}

function enableSendingCodeToggled() {
    g_sendFromCode = !g_sendFromCode;

    if (g_sendFromCode) {
        g_sendFromJoystick = false;
    }

    updateSendingButtons();
}

////////////////////////////////////////////////////////////////////////////////

function endReplay(goLive) {
    fetch('/endreplay', { method: 'post',
                        headers: {
                            'Accept': 'application/json, text/plain, */*',
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({endReplay: true})
                       }
    )
    .then(function(response) {
        if (response.ok) {
            if (goLive) {
                window.location = "/";
            }
            else {
                window.location = "/recordings";
            }
            return;
        }
        throw new Error('Request failed.');
        })
    .catch(function(error) {
        console.log(error);
    });
}


function remotePlayer(value) {
    var commandValue = 0;
    if ('playButton' == value) {
        g_userIsSteppingForward = false;
        if ("play" == g_buttonPlayState) {
            g_buttonPlayState = "pause";
            $("#playButton").removeClass("fas fa-pause").addClass("fas fa-play");
            commandValue = 2;
        }
        else if ("pause" == g_buttonPlayState) {
            g_buttonPlayState = "play";
            $("#playButton").removeClass("fas fa-play").addClass("fas fa-pause");
            commandValue = 1;
        }
    }
    if ('stepForwardButton' == value) {
        g_userIsSteppingForward = true;
        g_buttonPlayState = "pause";
        $("#playButton").removeClass("fas fa-pause").addClass("fas fa-play");
        commandValue = 4;
    }

    if ('replayStartOver' == value) {
        // Restart playback.
        if ("play" == g_buttonPlayState) {
            $("#playButton").removeClass("fas fa-play").addClass("fas fa-pause");
        }
        g_buttonPlayState = "play";
        commandValue = 1;

        // Send seekTo beginning function.
        setTimeout(function() {
            // Seek to beginning.
            var remotePlayerJSON = "{\"command\":3,\"seekTo\":0}";
            var output = g_libcluon.encodeEnvelopeFromJSONWithoutTimeStamps(remotePlayerJSON, 9 /* message identifier */, 0  /* sender stamp */);
            var commandJSON = "{\"remoteplayback\":" + "\"" + window.btoa(output) + "\"" + "}";

            g_ws.send(commandJSON);
            var slider = document.getElementById("playbackrange");
            slider.value = 1;
        }, 300);
    }

    var remotePlayerJSON = "{\"command\":" + commandValue + "}";

    var output = g_libcluon.encodeEnvelopeFromJSONWithoutTimeStamps(remotePlayerJSON, 9 /* message identifier */, 0  /* sender stamp */);

//        strToAB = str =>
//          new Uint8Array(str.split('')
//            .map(c => c.charCodeAt(0))).buffer;

// Instead of sending the raw bytes, we encapsulate them into a JSON object.
//        g_ws.send(strToAB(output), { binary: true });

    var commandJSON = "{\"remoteplayback\":" + "\"" + window.btoa(output) + "\"" + "}";
    g_ws.send(commandJSON);
}

function prune_oflow_points(context) {
    var n = point_count;
    var i=0,j=0;
    const pruned_points = []
    for(; i < n; ++i) {
        if(point_status[i] == 1) {
            if(j < i) {
                curr_xy[j<<1] = curr_xy[i<<1];
                curr_xy[(j<<1)+1] = curr_xy[(i<<1)+1];
            }
            draw_circle(context, curr_xy[j<<1], curr_xy[(j<<1)+1]);
            pruned_points.push(curr_xy[j<<1]);
            pruned_points.push(curr_xy[(j<<1) + 1]);
            ++j;
        }
    }
    point_count = j;
    return pruned_points;
}

function draw_circle(context, x, y) {
    context.beginPath();
    context.arc(x, y, 4, 0, Math.PI*2, true);
    context.closePath();
    context.fill();
}

/*function determineCenter(points) {
    const topLeft = determineTopLeftCorner(points)
    const boxSize = determineBoxSize(points);
    return [
        topLeft[0] + boxSize[0] / 2,
        topLeft[1] + boxSize[1] / 2
    ]
}*/

function determineTopLeftCorner(points) {
    let topLeft = [1000, 1000]
    for (i = 0; i < points.length; i=i+2) {
        topLeft[0]=Math.min(points[i],topLeft[0]) 
		topLeft[1]=Math.min(points[i+1],topLeft[1])
    }
    return topLeft
}

function determineBoxSize(points)  {

	var minY=100000
	var maxY=-100000
	var minX=100000
	var maxX=-100000
	
	for (i = 0; i < points.length; i=i+2) { 
		minY=Math.min(points[i+1],minY)
		maxY=Math.max(points[i+1],maxY)
		
		minX=Math.min(points[i],minX)
		maxX=Math.max(points[i],maxX)
	}
	
	return[maxX-minX, maxY-minY]

}

function setControls(centroid, deviation) {
    window.centroid = centroid;
    window.deviation = deviation;
    let groundSteering = window.steeringReq || 0;
    let pedalPosition = window.PedalPosReq || 0;
    const editor = ace.edit("editor");
    controllerCode = editor.getValue();
    eval(controllerCode);
    console.log(`Centroid: ${centroid}, Deviation: ${deviation}`);
    console.log(`Pedal position: ${pedalPosition}, Steering position: ${groundSteering}`);
    const groundSteeringRequest = `{\"groundSteering\":${groundSteering}}`;
    const envGroundSteeringRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(groundSteeringRequest, 1090 /* message identifier */, 0 /* sender stamp */);

    const pedalPositionRequest = `{\"position\":${pedalPosition}`;
    const envPedalPositionRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(pedalPositionRequest, 1086 /* message identifier */, 0 /* sender stamp */);

    const actuationRequest = "{\"acceleration\":0,\"steering\":0,\"isValid\":false}";
    const envActuationRequest = g_libcluon.encodeEnvelopeFromJSONWithSampleTimeStamp(actuationRequest, 160 /* message identifier */, 0 /* sender stamp */);

    var actuationCommands = "{\"virtualjoystick\":" +
                                    "{" +
                                        "\"pedalPositionRequest\":" + "\"" + window.btoa(envPedalPositionRequest) + "\"," +
                                        "\"groundSteeringRequest\":" + "\"" + window.btoa(envGroundSteeringRequest) + "\"," +
                                        "\"actuationRequest\":" + "\"" + window.btoa(envActuationRequest) + "\"" +
                                    "}" +
                                "}";
    g_ws.send(actuationCommands);
};

function controlReq(track, dist,Psteer,Ppedal,Ipedal,Dpedal,dt,resetIntegral) {
    
    var PedalPosReq=0
    var steeringReq=0
    if(window.controllerRuninng){
        if(resetIntegral===1){
            controllerParams.integral=0
        }

        if (controllerParams.prevDist) {
            error=-(dist-controllerParams.targetDist)

            let PedalPosReqPpart=Ppedal*error
            let derivative=(error-controllerParams.prevError)/dt
            controllerParams.integral=controllerParams.integral+error*dt
            let PedalPosReqDpart=Dpedal*derivative
            let PedalPosReqIpart=controllerParams.integral*Ipedal

            PedalPosReq=PedalPosReqPpart+PedalPosReqIpart+PedalPosReqDpart

            controllerParams.prevDist=dist
            controllerParams.prevError=error

            let normalizeDistToCenter=2*(track[0]-(canvasWidth/2))/canvasWidth

            if(PedalPosReq>=0.07){
                steeringReq=Psteer*normalizeDistToCenter
            }else if(PedalPosReq<=-0.07){
                steeringReq=-Psteer*normalizeDistToCenter
            }else{
                steeringReq=0
            }
            console.log(controllerParams)
        } else {
            controllerParams.integral=0
            controllerParams.prevDist=dist
            controllerParams.targetDist=dist
            controllerParams.prevError=0

        /*	controllerParams.Psteer=0.3
            controllerParams.Ppedal=0.3
            controllerParams.Dpedal=0 */
        // controllerParams.dt=0.1
        }
    }
    window.PedalPosReq = PedalPosReq
    window.steeringReq = steeringReq
    return [PedalPosReq,steeringReq]
}

document.getElementById("run-button").addEventListener("click", function( event ) {
    if(!window.controllerRuninng){
        window.controllerRuninng = true;
       $('#run-button').removeClass('fas fa-toggle-off').addClass('fas fa-toggle-on');
       $('#run-button').css('color', '#3CB371');
    } else {
        window.controllerRuninng = false;
        $('#run-button').removeClass('fas fa-toggle-on').addClass('fas fa-toggle-off');
        $('#run-button').css('color', '#555');
    }
                                
});
