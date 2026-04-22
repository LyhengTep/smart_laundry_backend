
import json
import logging

from app.db.engine import get_session_context
from app.modules.drivers.models import DARole
from app.modules.drivers.service import auto_assign_driver


logger = logging.getLogger(__name__)

async def handle_pickup_assignment(message: dict) -> None:
    logger.info(f"Handling pickup assignment message: {message['MessageId']}")

    async with get_session_context() as session:
        # Here you would implement the logic to process the pickup assignment message
        # For example, you might parse the message body, update the database, etc.
        message_body = json.loads(message.get("Body"))
        logger.info(f"Processing pickup assignment for order_id: {message_body}")
        await auto_assign_driver(session=session, type=DARole.PICKUP, order_id=message_body.get("order_id"))



async def handle_delivery_assignment(message: dict) -> None:
    logger.info(f"Handling pickup assignment message: {message['MessageId']}")

    async with get_session_context() as session:
        # Here you would implement the logic to process the pickup assignment message
        # For example, you might parse the message body, update the database, etc.
        message_body = json.loads(message.get("Body"))
        logger.info(f"Processing pickup assignment for order_id: {message_body}")
        await auto_assign_driver(session=session, type=DARole.DELIVERY, order_id=message_body.get("order_id"))