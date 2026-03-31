from __future__ import annotations

from collections import defaultdict
import logging
from typing import Any


from fastapi import WebSocket

logger = logging.getLogger(__name__)
class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, room: str, websocket: WebSocket) -> None:
        logger.info("Connect ===>")
        await websocket.accept()
        self._rooms[room].add(websocket)

    def disconnect(self, room: str, websocket: WebSocket) -> None:
        room_connections = self._rooms.get(room)
        if room_connections is None:
            return

        room_connections.discard(websocket)
        if not room_connections:
            self._rooms.pop(room, None)

    async def send_json(self, room: str, payload: dict[str, Any]) -> None:
        for websocket in list(self._rooms.get(room, set())):
            await websocket.send_json(payload)

    def connection_count(self, room: str) -> int:
        return len(self._rooms.get(room, set()))


connection_manager = ConnectionManager()
