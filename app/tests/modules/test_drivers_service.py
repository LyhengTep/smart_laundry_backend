from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.drivers import service as driver_service
from app.modules.drivers.models import Driver
from app.modules.drivers.schema import DriverWrite
from app.modules.users.models import RoleName, User, UserStatus
from app.modules.users.schema import UserEdit
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_driver() -> Driver:
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid4(),
        full_name="Driver User",
        user_name="driver",
        email="driver@example.com",
        phone=None,
        password_hash="hashed",
        role=RoleName.DRIVER,
        status=UserStatus.INACTIVE,
        created_at=now,
        updated_at=now,
    )
    return Driver(
        id=uuid4(),
        user_id=user.id,
        plate_number="ABC123",
        id_card_number="ID123",
        vehicle_type="Bike",
        license_number=None,
        vehicle_color="Red",
        user=user,
    )


def test_approve_driver_sets_user_active() -> None:
    driver = build_driver()
    session = FakeAsyncSession(exec_results=[driver])

    result = run_async(driver_service.approve_driver(session, str(driver.id)))

    assert result.user.status == UserStatus.ACTIVE
    assert session.commits == 1


def test_list_one_driver_raises_not_found() -> None:
    session = FakeAsyncSession(exec_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(driver_service.list_one_driver(session, str(uuid4())))

    assert exc.value.status_code == 404


def test_edit_driver_updates_driver_and_user_fields() -> None:
    driver = build_driver()
    session = FakeAsyncSession(exec_results=[driver])
    data = DriverWrite(
        plate_number="NEW123",
        id_card_number="NEWID",
        vehicle_type="Car",
        license_number="LIC123",
        vehicle_color="Blue",
        user=UserEdit(
            full_name="Updated Driver",
            user_name="updated_driver",
            password="secret",
            email="updated@example.com",
            phone="555",
            role=RoleName.DRIVER,
            status=UserStatus.ACTIVE,
        ),
    )

    updated = run_async(driver_service.edit_driver(session, driver.id, data))

    assert updated.plate_number == "NEW123"
    assert updated.user.full_name == "Updated Driver"
    assert session.commits == 1

