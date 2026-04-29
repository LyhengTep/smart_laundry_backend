from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import NoResultFound

from app.modules.auth import service as auth_service
from app.modules.auth.schema import LoginRequest, LogoutRequest, SignupRequest
from app.modules.drivers.models import Driver, DriverStatus
from app.modules.users.models import RoleName, User, UserStatus
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        full_name="Auth User",
        user_name="authuser",
        email="auth@example.com",
        phone=None,
        msg_token=None,
        password_hash="hashed",
        role=RoleName.CUSTOMER,
        status=UserStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_login_returns_token(monkeypatch: pytest.MonkeyPatch) -> None:
    user = build_user()
    session = FakeAsyncSession(exec_results=[user])
    monkeypatch.setattr(auth_service, "create_access_token", lambda user_id: f"token::{user_id}")
    monkeypatch.setattr(auth_service, "verify_password", lambda raw, hashed: True)

    response = run_async(
        auth_service.login(
            LoginRequest(login=user.user_name, password="secret", role=RoleName.CUSTOMER),
            session,
        )
    )

    assert response.token == f"token::{user.id}"
    assert response.user_name == user.user_name


def test_login_does_not_commit_for_customer(monkeypatch: pytest.MonkeyPatch) -> None:
    user = build_user()
    session = FakeAsyncSession(exec_results=[user])
    monkeypatch.setattr(auth_service, "create_access_token", lambda user_id: f"token::{user_id}")
    monkeypatch.setattr(auth_service, "verify_password", lambda raw, hashed: True)

    response = run_async(
        auth_service.login(
            LoginRequest(
                login=user.user_name,
                password="secret",
                role=RoleName.CUSTOMER,
            ),
            session,
        )
    )

    assert user.msg_token is None
    assert session.commits == 0


def test_login_raises_not_found_for_invalid_password(monkeypatch: pytest.MonkeyPatch) -> None:
    user = build_user()
    session = FakeAsyncSession(exec_results=[user])
    monkeypatch.setattr(auth_service, "verify_password", lambda raw, hashed: False)

    with pytest.raises(Exception) as exc:
        run_async(
            auth_service.login(
                LoginRequest(login=user.user_name, password="wrong", role=RoleName.CUSTOMER),
                session,
            )
        )

    assert getattr(exc.value, "status_code", None) == 404


def test_login_raises_not_found_for_missing_user() -> None:
    session = FakeAsyncSession(exec_results=[NoResultFound()])

    with pytest.raises(Exception) as exc:
        run_async(
            auth_service.login(
                LoginRequest(login="missing", password="secret", role=RoleName.CUSTOMER),
                session,
            )
        )

    assert getattr(exc.value, "status_code", None) == 404


def test_signup_rejects_existing_user() -> None:
    session = FakeAsyncSession(exec_results=[object(), None])
    data = SignupRequest(
        full_name="Taken User",
        user_name="taken",
        password="secret",
        email="taken@example.com",
        phone=None,
        role=RoleName.CUSTOMER,
    )

    with pytest.raises(Exception) as exc:
        run_async(auth_service.signup(data, session))

    assert getattr(exc.value, "status_code", None) == 400


def test_logout_clears_customer_msg_token() -> None:
    user = build_user()
    user.msg_token = "firebase-token"
    session = FakeAsyncSession(get_results=[user], exec_results=[[]])

    response = run_async(
        auth_service.logout(
            LogoutRequest(user_id=user.id, role=RoleName.CUSTOMER),
            session,
        )
    )

    assert response == {"message": "Logout successful"}
    assert user.msg_token is None
    assert session.commits == 2


def test_logout_sets_driver_offline_and_clears_token() -> None:
    user = build_user()
    user.role = RoleName.DRIVER
    user.msg_token = "firebase-token"
    driver = Driver(
        id=uuid4(),
        user_id=user.id,
        plate_number="ABC123",
        id_card_number="ID123",
        vehicle_type="Bike",
        driver_status=DriverStatus.ONLINE,
        license_number=None,
        vehicle_color="Red",
    )
    session = FakeAsyncSession(get_results=[user], exec_results=[[], driver])

    response = run_async(
        auth_service.logout(
            LogoutRequest(user_id=user.id, role=RoleName.DRIVER),
            session,
        )
    )

    assert response == {"message": "Logout successful"}
    assert user.msg_token is None
    assert driver.driver_status == DriverStatus.OFFLINE
    assert session.commits == 2
