import boto3
import json
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


class SQSClient:
    def __init__(self, queue_name: str, region: str = "us-east-2"):
        self.queue_name = queue_name
        self.region = region
        self.sqs = boto3.resource("sqs", region_name=region)
        self.queue = self._get_queue()

    def _get_queue(self):
        try:
            queue = self.sqs.get_queue_by_name(QueueName=self.queue_name)
            print(f"[SQSClient] Connected to queue: {queue.url}")
            return queue
        except Exception as e:
            raise RuntimeError(f"[SQSClient] Failed to get SQS queue: {e}")

    def send_message(self, message_body: dict):
        try:
            response = self.queue.send_message(
                MessageBody=json.dumps(message_body, cls=DecimalEncoder)
            )
            print(f"[SQSClient] Message sent to SQS: {response}")
            return response
        except Exception as e:
            raise RuntimeError(f"[SQSClient] Failed to send message: {e}")
