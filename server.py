from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Chat</title>
</head>
<body>
<h1>Simple Chat</h1>
<textarea id="messages" cols="40" rows="10" readonly></textarea><br>
<input id="msgInput" type="text">
<button onclick="sendMessage()">Send</button>

<script>
    // Використовуємо WSS для HTTPS та динамічний хост
    var ws = new WebSocket(`wss://${window.location.host}/ws`);

    ws.onopen = function() {
        console.log("WebSocket connected!");
    }

    ws.onmessage = function(event) {
        document.getElementById("messages").value += event.data + "\\n";
    };

    ws.onerror = function(event) {
        console.error("WebSocket error:", event);
    };

    function sendMessage() {
        let text = document.getElementById("msgInput").value;
        ws.send(text);
        document.getElementById("msgInput").value = "";
    }
</script>
</body>
</html>
"""

@app.get("/")
def get():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_text()
        await ws.send_text(f"Message: {data}")
