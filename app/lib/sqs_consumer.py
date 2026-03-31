import json
from botocore.client import BaseClient
from typing import Callable

class SQSConsumer:
    def __init__(self, client: BaseClient, queue_url: str):
        self.client = client
        self.queue_url = queue_url

    def poll(self):
        response = self.client.receive_message(
            QueueUrl=self.queue_url,
            WaitTimeSeconds=10
        )
        return response.get("Messages", [])

    def delete(self, receipt_handle: str):
        self.client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle
        )

    def start(self, handler: Callable):
        while True:
            messages = self.poll()

            for msg in messages:
                try:
                    data = json.loads(msg["Body"])
                    handler(data)

                    self.delete(msg["ReceiptHandle"])
                except Exception as e:
                    print("Error:", e)