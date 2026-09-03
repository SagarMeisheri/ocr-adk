"""WebSocket hub for real-time live event streaming to UI and local daemon."""

from __future__ import annotations
import json
import asyncio
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["Realtime WebSockets"])


class ConnectionManager:
    """Manages active WebSocket browser clients."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        dead_connections = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)


ws_manager = ConnectionManager()


@router.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    """UI connects here to receive real-time notifications (upload progress, sync updates)."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo ping-pong if needed
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
