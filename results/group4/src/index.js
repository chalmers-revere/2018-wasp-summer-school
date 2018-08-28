const libcluon = require('./lib/libcluon.js');
const io = require('socket.io-client');
const __libcluon = libcluon();
const socket = io('ws://kiwi.opendlv.io', {path: '/od4'});
socket.binaryType = 'arraybuffer';

socket.on('connection', () => {
    console.log('Connected.');
});

socket.on('message', (event) => {
    const data = JSON.parse(__libcluon.decodeEnvelopeToJSON(event.data));
    console.log(data);
});

socket.on('close', () => {
    console.log('Connection closed.');
});
// console.log(libcluon);