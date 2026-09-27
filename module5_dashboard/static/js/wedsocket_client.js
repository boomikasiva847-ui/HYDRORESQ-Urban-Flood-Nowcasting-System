// ============================================================
// HYDRORESQ - MODULE 4 WEBSOCKET CLIENT
// ============================================================


function updateWebSocketUI(connected, text) {
    const wsDot = document.getElementById('ws-dot');
    const wsStatusText = document.getElementById('ws-status-text');
    const settingsStatus = document.getElementById('settings-ws-status');
    if (wsDot) wsDot.className = connected ? 'dot connected' : 'dot disconnected';
    if (wsStatusText) wsStatusText.textContent = text;
    if (settingsStatus) {
        settingsStatus.textContent = connected ? '● Connected' : `● ${text}`;
        settingsStatus.classList.toggle('online', connected);
    }
}

function initWebSocket() {

    const WS_URL =
        'ws://127.0.0.1:8000/ws';


    const wsDot =
        document.getElementById(
            'ws-dot'
        );


    const wsStatusText =
        document.getElementById(
            'ws-status-text'
        );


    const socket =
        new WebSocket(WS_URL);
    let pingTimer = null;


    // ========================================================
    // CONNECTED
    // ========================================================

    socket.onopen = () => {

        updateWebSocketUI(true, 'Live Feed Connected');


        pingTimer = setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) socket.send('ping');
        }, 25000);

        console.log(
            '[WebSocket] Connected to Module 4.'
        );
    };


    // ========================================================
    // NEW FORECAST
    // ========================================================

    socket.onmessage = event => {

        try {

            const data =
                JSON.parse(
                    event.data
                );


            if (
                data &&
                Array.isArray(data)
            ) {

                console.log(
                    '[WebSocket] Live forecast received:',
                    data.length,
                    'records'
                );


                // Update cache

                cachedForecast =
                    data;


                // Find currently selected slider step

                const slider =
                    document.getElementById(
                        'time-slider'
                    );


                const currentStep =
                    slider
                        ? Number(slider.value)
                        : 0;


                // Re-render map

                renderCycle(
                    currentStep
                );
            }

        }

        catch (error) {

            console.error(
                '[WebSocket] Invalid message:',
                error
            );

        }
    };


    // ========================================================
    // CLOSED
    // ========================================================

    socket.onclose = () => {
        if (pingTimer) {
            clearInterval(pingTimer);
            pingTimer = null;
        }

        updateWebSocketUI(false, 'Disconnected (Retrying...)');


        console.warn(
            '[WebSocket] Connection closed.'
        );


        setTimeout(
            initWebSocket,
            5000
        );
    };


    // ========================================================
    // ERROR
    // ========================================================

    socket.onerror = error => {

        console.warn(
            '[WebSocket] Connection error:',
            error
        );


        socket.close();
    };
}


// ============================================================
// PAGE LOAD
// ============================================================

document.addEventListener(
    'DOMContentLoaded',
    initWebSocket
);