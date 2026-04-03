


# --- Main poll loop ---

import asyncio
import json
import logging

from httpx import get


from app.consumer.handlers.assignment_handler import handle_pickup_assignment
from app.core.config import TOPIC_PICKUP_ASSIGNMENT
from app.lib.aws import get_or_create_queue, get_sqs_client


logger = logging.getLogger(__name__)



HANDLERS={
    "PICKUP": handle_pickup_assignment,
}



async def process_message(message: dict, sem: asyncio.Semaphore) -> None:
    async with sem:
        try:
            logger.info(f"Processing message: {message['MessageId']}")
            body = json.loads(message["Body"])
            event_type = body.get("type")
            handler = HANDLERS.get(event_type)
            if not handler:
                logger.warning(f"No handler for message type: {event_type}")
                return
            # Simulate processing time
            await handler(message)
            logger.info(f"Finished processing message: {message['MessageId']}")

        except Exception as e:
            logger.error(f"Error processing message {message['MessageId']}: {e}", exc_info=True)
            pass 
        finally:
            print(f"Deleting message {message['MessageId']} from queue")
            sqs_client = get_sqs_client()
            # Delete the message from the queue after processing
            sqs_client.delete_message(
                QueueUrl=get_or_create_queue(queue_name=TOPIC_PICKUP_ASSIGNMENT,sqs=sqs_client),
                ReceiptHandle=message['ReceiptHandle']
            )

def poll_sqs():
        sqs_client = get_sqs_client()
        topic_url = get_or_create_queue(queue_name=TOPIC_PICKUP_ASSIGNMENT, sqs=sqs_client)
        return sqs_client.receive_message(
            QueueUrl=topic_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20
        ).get("Messages", [])

async def consume(sem: asyncio.Semaphore) -> None:
    logger.info("SQS consumer started")
    loop = asyncio.get_event_loop()
    while True:
        try:
            messages = await loop.run_in_executor(None, poll_sqs)

            if not messages:
                continue

            logger.debug(f"Received {len(messages)} message(s)")
            await asyncio.gather(
                *[process_message(m, sem) for m in messages]
            )
            await asyncio.sleep(1)  
        except asyncio.CancelledError:
            logger.info("SQS consumer shutting down gracefully")
            break

        except Exception as e:
            logger.error(f"Poll loop error: {e}", exc_info=True)
            await asyncio.sleep(5)

