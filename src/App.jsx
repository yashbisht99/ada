import React from 'react';
import io from 'socket.io-client';

import { useAdaSocketState } from './hooks/useAdaSocketState';
import OrbAdaApp from './new-orb/OrbAdaApp';
import './new-orb/index.css';

const socket = io('http://localhost:8000');

const { ipcRenderer } = window.require ? window.require('electron') : {
    ipcRenderer: {
        send: (channel, ...args) => console.log(`[IPC Mock] Sending: ${channel}`, args),
        on: (channel) => console.log(`[IPC Mock] Listening: ${channel}`),
        removeListener: (channel) => console.log(`[IPC Mock] Removing listener: ${channel}`),
    },
};

function App() {
    const hud = useAdaSocketState(socket, ipcRenderer);

    return <OrbAdaApp socket={socket} hud={hud} />;
}

export default App;
