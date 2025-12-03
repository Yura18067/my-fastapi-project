from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi_socketio import SocketManager

app = FastAPI()
sio = SocketManager(app=app, mount_location="/ws")  # WebSocket маршрут /ws

html = """
<!DOCTYPE html>
<html>
<head>
    <title>Socket.IO Chat</title>
</head>
<body>
<h1>Simple Chat</h1>
<textarea id="messages" cols="40" rows="10" readonly></textarea><br>
<input id="msgInput" type="text">
<button onclick="sendMessage()">Send</button>

<script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
<script>
    var socket = io("/ws");  // Підключаємося до Socket.IO на /ws

    socket.on('message', function(msg) {
        document.getElementById("messages").value += msg + "\\n";
    });

    function sendMessage() {
        let text = document.getElementById("msgInput").value;
        if(text.trim() !== "") {
            socket.emit('message', text);
            document.getElementById("msgInput").value = "";
        }
    }
</script>
</body>
</html>
"""

@app.get("/")
def get():
    return HTMLResponse(html)

@sio.on('message')
async def handle_message(sid, msg):
    # Відправляємо повідомлення всім підключеним клієнтам
    await sio.emit('message', f'You: {msg}')
