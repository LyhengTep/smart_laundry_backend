from io import BytesIO

import pytest
from fastapi import UploadFile

from app.modules.files import service as file_service
from app.tests.modules.conftest import run_async


async def _fake_upload_success(*_args, **_kwargs):
    return {
        "bucket": "test-bucket",
        "key": "public/abc_receipt.txt",
        "url": "https://cdn.example.com/public/abc_receipt.txt",
    }


async def _fake_upload_failure(*_args, **_kwargs):
    from app.exceptions.http import create_500
    raise create_500("S3 upload failed")


def test_upload_file_returns_public_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(file_service, "upload_upload_file_to_s3", _fake_upload_success)

    file = UploadFile(filename="receipt.txt", file=BytesIO(b"hello"))
    result = run_async(file_service.upload_file(file))

    assert result.filename == "receipt.txt"
    assert result.url == "https://cdn.example.com/public/abc_receipt.txt"
    assert result.path == "public/abc_receipt.txt"


def test_upload_file_raises_500_on_s3_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(file_service, "upload_upload_file_to_s3", _fake_upload_failure)

    file = UploadFile(filename="broken.txt", file=BytesIO(b"hello"))
    with pytest.raises(Exception) as exc:
        run_async(file_service.upload_file(file))

    assert getattr(exc.value, "status_code", None) == 500
