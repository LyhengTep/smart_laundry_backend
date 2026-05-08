from __future__ import annotations

from pathlib import PurePosixPath
from typing import BinaryIO
from uuid import uuid4
from mypy_boto3_sqs import SQSClient
import boto3
from fastapi import UploadFile

from app.core.config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_S3_BUCKET,
    AWS_S3_ENDPOINT_URL,
    AWS_S3_PUBLIC_BASE_URL,
    AWS_SQS_ENDPOINT_URL,
    AWS_SQS_QUEUE_URL,
    AWS_SECRET_ACCESS_KEY,
)
from app.exceptions.http import create_500


def get_boto3_session()->boto3.session.Session:
    return boto3.session.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def get_s3_client():
    session = get_boto3_session()
    print(f"Creating S3 client with endpoint: {AWS_S3_ENDPOINT_URL}")
    return session.client("s3")


def get_sqs_client()->SQSClient:
    session = get_boto3_session()
    return session.client("sqs", endpoint_url=AWS_SQS_ENDPOINT_URL)



def get_or_create_queue(sqs, queue_name: str):
    # print(f"Getting or creating SQS queue: {queue_name}")
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        return response["QueueUrl"]
    except sqs.exceptions.QueueDoesNotExist:
        response = sqs.create_queue(QueueName=queue_name)
        return response["QueueUrl"]

def get_s3_bucket_name() -> str:
    if not AWS_S3_BUCKET:
        raise create_500("AWS_S3_BUCKET is not configured")
    return AWS_S3_BUCKET


def get_sqs_queue_url() -> str:
    if not AWS_SQS_QUEUE_URL:
        raise create_500("AWS_SQS_QUEUE_URL is not configured")
    return AWS_SQS_QUEUE_URL


def sanitize_filename(filename: str) -> str:
    return PurePosixPath(filename).name.replace(" ", "_")


def build_s3_key(filename: str, folder: str = "uploads") -> str:
    safe_name = sanitize_filename(filename)
    normalized_folder = folder.strip("/").replace("\\", "/")
    return f"{normalized_folder}/{uuid4().hex}_{safe_name}"


def build_s3_public_url(key: str, bucket: str | None = None) -> str:
    bucket_name = bucket or get_s3_bucket_name()
    if AWS_S3_PUBLIC_BASE_URL:
        return f"{AWS_S3_PUBLIC_BASE_URL.rstrip('/')}/{key.lstrip('/')}"

    if AWS_REGION:
        return f"https://{bucket_name}.s3.{AWS_REGION}.amazonaws.com/{key}"
    return f"https://{bucket_name}.s3.amazonaws.com/{key}"


def upload_bytes_to_s3(
    content: bytes,
    filename: str,
    *,
    content_type: str | None = None,
    folder: str = "uploads",
    bucket: str | None = None,
) -> dict[str, str]:
    key = build_s3_key(filename=filename, folder=folder)
    client = get_s3_client()
    bucket_name = bucket or get_s3_bucket_name()
    print(f"Uploading file to S3: bucket={bucket_name}, key={key}, content_type={content_type}")
    extra_args: dict[str, str] = {}
    if content_type:
        extra_args["ContentType"] = content_type

    client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=content,
        **extra_args,
    )
    return {
        "bucket": bucket_name,
        "key": key,
        "url": build_s3_public_url(key=key, bucket=bucket_name),
    }


async def upload_upload_file_to_s3(
    file: UploadFile,
    *,
    folder: str = "uploads",
    bucket: str | None = None,
) -> dict[str, str]:
    try:
        content = await file.read()
        return upload_bytes_to_s3(
            content=content,
            filename=file.filename or "upload.bin",
            content_type=file.content_type,
            folder=folder,
            bucket=bucket,
        )
    except Exception as exc:
        raise create_500(f"Failed to upload file to AWS S3: {exc}") from exc


def send_sqs_message(
    message_body: str,
    *,
    queue_name: str | None = None,
    message_attributes: dict | None = None,
    delay_seconds: int | None = None,
    group_id: str | None = None,
    deduplication_id: str | None = None,
) -> dict:
    client = get_sqs_client()

    if queue_name is not None:
        resolved_queue_url = get_or_create_queue(client, queue_name=queue_name)
    else:
        resolved_queue_url = get_sqs_queue_url()

    payload: dict = {
        "QueueUrl": resolved_queue_url,
        "MessageBody": message_body,
    }
    if message_attributes:
        payload["MessageAttributes"] = message_attributes
    if delay_seconds is not None:
        payload["DelaySeconds"] = delay_seconds
    if group_id is not None:
        payload["MessageGroupId"] = group_id
    if deduplication_id is not None:
        payload["MessageDeduplicationId"] = deduplication_id

    return client.send_message(**payload)


def receive_sqs_messages(
    *,
    queue_url: str | None = None,
    max_number_of_messages: int = 1,
    wait_time_seconds: int = 0,
    visibility_timeout: int | None = None,
    attribute_names: list[str] | None = None,
    message_attribute_names: list[str] | None = None,
) -> list[dict]:
    client = get_sqs_client()
    resolved_queue_url = queue_url or get_sqs_queue_url()

    payload: dict = {
        "QueueUrl": resolved_queue_url,
        "MaxNumberOfMessages": max_number_of_messages,
        "WaitTimeSeconds": wait_time_seconds,
        "AttributeNames": attribute_names or ["All"],
        "MessageAttributeNames": message_attribute_names or ["All"],
    }
    if visibility_timeout is not None:
        payload["VisibilityTimeout"] = visibility_timeout

    response = client.receive_message(**payload)
    return response.get("Messages", [])


def delete_sqs_message(receipt_handle: str, *, queue_url: str | None = None) -> dict:
    client = get_sqs_client()
    resolved_queue_url = queue_url or get_sqs_queue_url()
    return client.delete_message(
        QueueUrl=resolved_queue_url,
        ReceiptHandle=receipt_handle,
    )
