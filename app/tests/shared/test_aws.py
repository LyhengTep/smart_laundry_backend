from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import UploadFile

from app.lib import aws
from app.tests.modules.conftest import run_async


def test_build_s3_key_sanitizes_filename() -> None:
    key = aws.build_s3_key("my image.png", folder="receipts")

    assert key.startswith("receipts/")
    assert key.endswith("_my_image.png")


def test_build_s3_public_url_uses_public_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aws, "AWS_S3_PUBLIC_BASE_URL", "https://cdn.example.com")

    url = aws.build_s3_public_url("uploads/file.png", bucket="ignored")

    assert url == "https://cdn.example.com/uploads/file.png"


def test_upload_upload_file_to_s3_returns_bucket_key_and_url(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeS3Client:
        def put_object(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(aws, "get_s3_client", lambda: FakeS3Client())
    monkeypatch.setattr(aws, "get_s3_bucket_name", lambda: "smart-laundry")
    monkeypatch.setattr(aws, "build_s3_key", lambda filename, folder="uploads": f"{folder}/abc_{filename}")
    monkeypatch.setattr(
        aws,
        "build_s3_public_url",
        lambda key, bucket=None: f"https://cdn.example.com/{key}",
    )

    file = UploadFile(filename="avatar.png", file=BytesIO(b"hello"), headers={"content-type": "image/png"})
    result = run_async(aws.upload_upload_file_to_s3(file, folder="avatars"))

    assert result == {
        "bucket": "smart-laundry",
        "key": "avatars/abc_avatar.png",
        "url": "https://cdn.example.com/avatars/abc_avatar.png",
    }
    assert captured["Bucket"] == "smart-laundry"
    assert captured["Key"] == "avatars/abc_avatar.png"


def test_send_sqs_message_uses_configured_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeSQSClient:
        def send_message(self, **kwargs):
            captured.update(kwargs)
            return {"MessageId": "msg-1"}

    monkeypatch.setattr(aws, "get_sqs_client", lambda: FakeSQSClient())
    monkeypatch.setattr(aws, "get_sqs_queue_url", lambda: "https://sqs.example.com/queue")

    response = aws.send_sqs_message('{"event":"order.created"}')

    assert response == {"MessageId": "msg-1"}
    assert captured["QueueUrl"] == "https://sqs.example.com/queue"
    assert captured["MessageBody"] == '{"event":"order.created"}'


def test_receive_sqs_messages_returns_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSQSClient:
        def receive_message(self, **kwargs):
            return {"Messages": [{"Body": "hello", "ReceiptHandle": "r1"}]}

    monkeypatch.setattr(aws, "get_sqs_client", lambda: FakeSQSClient())
    monkeypatch.setattr(aws, "get_sqs_queue_url", lambda: "https://sqs.example.com/queue")

    messages = aws.receive_sqs_messages(wait_time_seconds=10)

    assert messages == [{"Body": "hello", "ReceiptHandle": "r1"}]


def test_get_s3_bucket_name_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aws, "AWS_S3_BUCKET", None)

    with pytest.raises(Exception) as exc:
        aws.get_s3_bucket_name()

    assert getattr(exc.value, "status_code", None) == 500


def test_get_sqs_queue_url_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aws, "AWS_SQS_QUEUE_URL", None)

    with pytest.raises(Exception) as exc:
        aws.get_sqs_queue_url()

    assert getattr(exc.value, "status_code", None) == 500


def test_send_sqs_message_supports_fifo_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeSQSClient:
        def send_message(self, **kwargs):
            captured.update(kwargs)
            return {"MessageId": "fifo-1"}

    monkeypatch.setattr(aws, "get_sqs_client", lambda: FakeSQSClient())
    monkeypatch.setattr(aws, "get_sqs_queue_url", lambda: "https://sqs.example.com/queue.fifo")

    response = aws.send_sqs_message(
        '{"event":"driver.assigned"}',
        group_id="order-1",
        deduplication_id="dedupe-1",
    )

    assert response == {"MessageId": "fifo-1"}
    assert captured["MessageGroupId"] == "order-1"
    assert captured["MessageDeduplicationId"] == "dedupe-1"


def test_delete_sqs_message_uses_receipt_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeSQSClient:
        def delete_message(self, **kwargs):
            captured.update(kwargs)
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    monkeypatch.setattr(aws, "get_sqs_client", lambda: FakeSQSClient())
    monkeypatch.setattr(aws, "get_sqs_queue_url", lambda: "https://sqs.example.com/queue")

    response = aws.delete_sqs_message("receipt-123")

    assert response == {"ResponseMetadata": {"HTTPStatusCode": 200}}
    assert captured == {
        "QueueUrl": "https://sqs.example.com/queue",
        "ReceiptHandle": "receipt-123",
    }
