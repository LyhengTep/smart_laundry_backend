from io import BytesIO
import builtins

import pytest
from fastapi import UploadFile

from app.modules.files import service as file_service
from app.tests.modules.conftest import run_async


def test_upload_file_returns_public_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builtins, "open", lambda *_args, **_kwargs: BytesIO())
    file = UploadFile(filename="receipt.txt", file=BytesIO(b"hello"))

    result = run_async(file_service.upload_file(file))

    assert result.filename == "receipt.txt"
    assert result.url == "/public/uploads/receipt.txt"


def test_upload_file_raises_500_on_write_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_open(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(builtins, "open", broken_open)
    file = UploadFile(filename="broken.txt", file=BytesIO(b"hello"))

    with pytest.raises(Exception) as exc:
        run_async(file_service.upload_file(file))

    assert getattr(exc.value, "status_code", None) == 500
