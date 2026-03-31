from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.modules.realtime.manager import connection_manager


router = APIRouter(tags=["realtime"])

logger = logging.getLogger(__name__)

async def _listen_forever(room: str, websocket: WebSocket) -> None:
    logger.info("call connect")
    await connection_manager.connect(room=room, websocket=websocket)
    await websocket.send_json(
        {
            "event": "subscribed",
            "room": room,
        }
    )
    try:
        while True:
            message = await websocket.receive_text()
            if message.lower() == "ping":
                await websocket.send_json({"event": "pong", "room": room})
    except WebSocketDisconnect as e:
        print(f"error ===> {e}")
        connection_manager.disconnect(room=room, websocket=websocket)


@router.websocket("/ws/orders/{order_id}")
async def order_updates(websocket: WebSocket, order_id: UUID) -> None:
    await _listen_forever(room=f"order:{order_id}", websocket=websocket)


# driver will listen to assignment updates for both pickup and delivery
@router.websocket("/ws/assignment/{driver_id}")
async def assignment_updates(websocket: WebSocket, driver_id: UUID) -> None:
    await _listen_forever(room=f"assignment:{driver_id}", websocket=websocket)



@router.websocket("/ws/users/{user_id}")
async def user_updates(websocket: WebSocket, user_id: UUID) -> None:
    await _listen_forever(room=f"user:{user_id}", websocket=websocket)



@router.websocket("/ws/testing")
async def testing(websocket: WebSocket) -> None:
    print("connected")
    await _listen_forever(room="testing", websocket=websocket)
