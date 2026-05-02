from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.users.models import RoleName, User, UserStatus
from app.modules.users.schema import UserEdit, UserMsgTokenUpdate, UserWrite
from app.modules.users import service as user_service
from app.tests.modules.conftest import FakeAsyncSession, run_async
from app.api.reponse_model import Page


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
    session = FakeAsyncSession(exec_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(user_service.list_one_user(uuid4(), session))

    assert exc.value.status_code == 404


def test_create_user_hashes_password_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    # exec_results=[None] satisfies the re-fetch after commit; side effects are checked on session.added
    session = FakeAsyncSession(exec_results=[None])
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

    run_async(user_service.create_user(data=data, session=session))

    added_user = session.added[0]
    assert added_user.password_hash == "hashed::secret"
    assert added_user.msg_token == "firebase-token"
    assert session.commits == 1


def test_delete_user_raises_404_when_missing() -> None:
    session = FakeAsyncSession(exec_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(user_service.delete_user(uuid4(), session))

    assert exc.value.status_code == 404


def test_delete_user_returns_true() -> None:
    user = build_user()
    session = FakeAsyncSession(exec_results=[user])

    result = run_async(user_service.delete_user(user.id, session))

    assert result is True
    assert session.commits == 1


def test_deactivate_user_sets_status_inactive() -> None:
    user = build_user()  # ACTIVE by default
    session = FakeAsyncSession(exec_results=[user, user])

    result = run_async(user_service.deactivate_user(user.id, session))

    assert result.status == UserStatus.INACTIVE
    assert session.commits == 1


def test_deactivate_user_raises_400_when_already_inactive() -> None:
    user = build_user()
    user.status = UserStatus.INACTIVE
    session = FakeAsyncSession(exec_results=[user])

    with pytest.raises(HTTPException) as exc:
        run_async(user_service.deactivate_user(user.id, session))

    assert exc.value.status_code == 400


def test_edit_user_updates_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    user = build_user()
    monkeypatch.setattr(user_service, "hash_password", lambda raw: f"hashed::{raw}")
    session = FakeAsyncSession(exec_results=[user, user])
    data = UserEdit(
        full_name="Updated Name",
        user_name="updated",
        password="newpass",
        email="updated@example.com",
        phone="999",
        role=RoleName.CUSTOMER,
        status=UserStatus.ACTIVE,
    )

    result = run_async(user_service.edit_user(user.id, data, session))

    assert result.full_name == "Updated Name"
    assert user.password_hash == "hashed::newpass"
    assert session.commits == 1


def test_edit_user_raises_404_when_missing() -> None:
    session = FakeAsyncSession(exec_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(user_service.edit_user(uuid4(), UserEdit(
            full_name="x", user_name="x", password="x",
            email="x@x.com", phone=None, role=RoleName.CUSTOMER, status=UserStatus.ACTIVE,
        ), session))

    assert exc.value.status_code == 404


def test_deactivate_user_raises_404_when_missing() -> None:
    session = FakeAsyncSession(exec_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(user_service.deactivate_user(uuid4(), session))

    assert exc.value.status_code == 404


def test_list_users_returns_page() -> None:
    user = build_user()
    # exec_results: [0] count query, [1] rows query
    session = FakeAsyncSession(exec_results=[1, [user]])

    result = run_async(user_service.list_users(session, page=1, size=10))

    assert isinstance(result, Page)
    assert result.total == 1
    assert result.items[0].id == user.id


def test_approve_user_sets_status_active() -> None:
    user = build_user()
    user.status = UserStatus.INACTIVE
    # exec_results: [0] fetch, [1] re-fetch after commit
    session = FakeAsyncSession(exec_results=[user, user])

    result = run_async(user_service.approve_user(user.id, session))

    assert result.status == UserStatus.ACTIVE
    assert session.commits == 1


def test_approve_user_raises_400_when_already_active() -> None:
    user = build_user()  # status is ACTIVE by default
    session = FakeAsyncSession(exec_results=[user])

    with pytest.raises(HTTPException) as exc:
        run_async(user_service.approve_user(user.id, session))

    assert exc.value.status_code == 400


def test_approve_user_raises_404_when_missing() -> None:
    session = FakeAsyncSession(exec_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(user_service.approve_user(uuid4(), session))

    assert exc.value.status_code == 404


def test_update_user_msg_token_updates_user() -> None:
    user = build_user()
    # exec_results: [0] find user, [1] re-fetch after commit
    session = FakeAsyncSession(exec_results=[user, user])

    updated = run_async(
        user_service.update_user_msg_token(
            user.id,
            UserMsgTokenUpdate(msg_token="firebase-device-token"),
            session,
        )
    )

    assert updated.msg_token == "firebase-device-token"
    assert session.commits == 1
