from __future__ import annotations

from app.modules.realtime.manager import ConnectionManager
from app.tests.modules.conftest import run_async


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.messages: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict) -> None:
        self.messages.append(payload)


def test_connection_manager_tracks_connections_and_broadcasts() -> None:
    manager = ConnectionManager()
    websocket = FakeWebSocket()

    run_async(manager.connect("order:123", websocket))
    run_async(manager.send_json("order:123", {"event": "test"}))

    assert websocket.accepted is True
    assert manager.connection_count("order:123") == 1
    assert websocket.messages == [{"event": "test"}]

    manager.disconnect("order:123", websocket)
    assert manager.connection_count("order:123") == 0
