# main.py
import json
from typing import Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from datetime import datetime
import asyncio

app = FastAPI()

# Примітивний менеджер з'єднань
rooms: Dict[str, Set[WebSocket]] = {}

# Монітор для блокування одночасного редагування rooms
rooms_lock = asyncio.Lock()

@app.get("/")
async def root():
    # просто перенаправимо на статичний файл
    return HTMLResponse(open("index.html", "r", encoding="utf-8").read())

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    current_room = None
    username = "Anonymous"
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                await ws.send_text(json.dumps({"type": "error", "text": "Invalid JSON"}))
                continue

            msg_type = msg.get("type")
            if msg_type == "join":
                # очікуємо: { type: "join", room: "room1", username: "Artem" }
                room = str(msg.get("room", "main"))
                username = str(msg.get("username", "Anonymous"))
                current_room = room
                async with rooms_lock:
                    conns = rooms.setdefault(room, set())
                    conns.add(ws)
                # повідомити іншим
                await broadcast(room, {
                    "type": "info",
                    "text": f"{username} приєднався",
                    "room": room,
                    "timestamp": now_iso()
                })
                # підтвердження клієнту
                await ws.send_text(json.dumps({"type": "joined", "room": room}))
            elif msg_type == "message":
                # очікуємо: { type: "message", room: "...", username: "...", text: "..." }
                room = msg.get("room", current_room)
                text = str(msg.get("text", ""))
                username = str(msg.get("username", username))
                if not room:
                    await ws.send_text(json.dumps({"type": "error", "text": "No room specified"}))
                    continue
                payload = {
                    "type": "message",
                    "room": room,
                    "username": username,
                    "text": text,
                    "timestamp": now_iso()
                }
                await broadcast(room, payload)
            elif msg_type == "leave":
                room = msg.get("room", current_room)
                if room:
                    await remove_from_room(room, ws)
            else:
                await ws.send_text(json.dumps({"type": "error", "text": f"Unknown type {msg_type}"}))
    except WebSocketDisconnect:
        # видалити з кімни
        if current_room:
            await remove_from_room(current_room, ws, announce_username=username)
    except Exception as e:
        # загальна помилка
        try:
            await ws.send_text(json.dumps({"type": "error", "text": f"Server error: {str(e)}"}))
        except:
            pass
        if current_room:
            await remove_from_room(current_room, ws, announce_username=username)

async def broadcast(room: str, message: dict):
    """Шлемо message (dict) усім коннекціям у room"""
    text = json.dumps(message)
    async with rooms_lock:
        conns = set(rooms.get(room, set()))
    # надсилаємо паралельно, пропускаючи падіння одного клієнта
    coros = []
    for conn in conns:
        coros.append(_safe_send(conn, text, room))
    await asyncio.gather(*coros)

async def _safe_send(conn: WebSocket, text: str, room: str):
    try:
        await conn.send_text(text)
    except Exception:
        # якщо не можемо відправити — прибрати
        await remove_from_room(room, conn)

async def remove_from_room(room: str, ws: WebSocket, announce_username: str = None):
    async with rooms_lock:
        conns = rooms.get(room)
        if not conns:
            return
        if ws in conns:
            conns.remove(ws)
        if not conns:
            # прибираємо кімнату якщо пусто
            rooms.pop(room, None)
    if announce_username:
        await broadcast(room, {
            "type": "info",
            "text": f"{announce_username} покинув чат",
            "room": room,
            "timestamp": now_iso()
        })

def now_iso():
    return datetime.utcnow().isoformat() + "Z"


