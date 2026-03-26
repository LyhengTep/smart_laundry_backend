from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.users.models import RoleName, User, UserStatus
from app.modules.users.schema import UserMsgTokenUpdate, UserWrite
from app.modules.users import service as user_service
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        full_name="Test User",
        user_name="tester",
        email="tester@example.com",
        phone="123",
        msg_token=None,
        password_hash="hashed",
        role=RoleName.CUSTOMER,
        status=UserStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_list_one_user_raises_404_when_missing() -> None:
    session = FakeAsyncSession(get_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(user_service.list_one_user(uuid4(), session))

    assert exc.value.status_code == 404


def test_create_user_hashes_password_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeAsyncSession()
    monkeypatch.setattr(user_service, "hash_password", lambda raw: f"hashed::{raw}")
    data = UserWrite(
        full_name="John Doe",
        user_name="jdoe",
        password="secret",
        email="john@example.com",
        phone=None,
        msg_token="firebase-token",
        role=RoleName.CUSTOMER,
    )

    created = run_async(user_service.create_user(data=data, session=session))

    assert created.password_hash == "hashed::secret"
    assert created.msg_token == "firebase-token"
    assert session.commits == 1
    assert session.refreshes == [created]


def test_delete_user_returns_false_when_missing() -> None:
    session = FakeAsyncSession(exec_results=[None])

    result = run_async(user_service.delete_user(str(uuid4()), session))

    assert result is False


def test_update_user_msg_token_updates_user() -> None:
    user = build_user()
    session = FakeAsyncSession(get_results=[user])

    updated = run_async(
        user_service.update_user_msg_token(
            user.id,
            UserMsgTokenUpdate(msg_token="firebase-device-token"),
            session,
        )
    )

    assert updated.msg_token == "firebase-device-token"
    assert session.commits == 1
