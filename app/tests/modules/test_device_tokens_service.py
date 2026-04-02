from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.device_tokens import service as device_token_service
from app.modules.device_tokens.models import DeviceToken
from app.modules.device_tokens.schema import DeviceTokenRegister
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_device_token() -> DeviceToken:
    now = datetime.now(timezone.utc)
    return DeviceToken(
        id=1,
        user_id=uuid4(),
        driver_id=None,
        token="token-1",
        device_type="ios",
        created_at=now,
        updated_at=now,
    )


def test_register_device_token_creates_new_token() -> None:
    session = FakeAsyncSession(exec_results=[None])
    data = DeviceTokenRegister(user_id=uuid4(), token="token-1", device_type="ios")

    created = run_async(device_token_service.register_device_token(data, session))

    assert created.token == "token-1"
    assert session.commits == 1


def test_register_device_token_updates_existing_token() -> None:
    existing = build_device_token()
    session = FakeAsyncSession(exec_results=[existing])
    data = DeviceTokenRegister(user_id=uuid4(), driver_id=uuid4(), token=existing.token, device_type="android")

    updated = run_async(device_token_service.register_device_token(data, session))

    assert updated.token == existing.token
    assert updated.device_type == "android"
    assert updated.driver_id == data.driver_id


def test_register_device_token_rejects_missing_target() -> None:
    session = FakeAsyncSession()

    with pytest.raises(HTTPException) as exc:
        run_async(
            device_token_service.register_device_token(
                DeviceTokenRegister(token="token-1", device_type="ios"),
                session,
            )
        )

    assert exc.value.status_code == 400


def test_get_device_token_raises_when_missing() -> None:
    session = FakeAsyncSession(get_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(device_token_service.get_device_token(1, session))

    assert exc.value.status_code == 404
