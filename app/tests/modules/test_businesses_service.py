from datetime import time
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.businesses import service as business_service
from app.modules.businesses.models import LaundryBusiness, ShopStatus
from app.modules.businesses.schema import BusinessWrite
from app.modules.users.models import RoleName, User, UserStatus
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_business(owner_id):
    return LaundryBusiness(
        id=uuid4(),
        owner_id=owner_id,
        name="Clean Place",
        address="Street 1",
        phone="123",
        latitude=11.0,
        longitude=104.0,
        profile_image_url=None,
        cover_image_url=None,
        business_license_number="LIC",
        rating_avg=0.0,
        open_time=time(8, 0),
        close_time=time(18, 0),
        status=ShopStatus.PENDING,
    )


def test_create_business_sets_owner_and_license() -> None:
    owner_id = uuid4()
    merchant = User(
        id=owner_id,
        full_name="Merchant",
        user_name="merchant",
        email="merchant@example.com",
        phone=None,
        password_hash="hashed",
        role=RoleName.MERCHANT,
        status=UserStatus.ACTIVE,
    )
    session = FakeAsyncSession(exec_results=[merchant])
    data = BusinessWrite(
        name="Laundry",
        address="Main street",
        phone="123",
        latitude=1.0,
        longitude=2.0,
        profile_image_url=None,
        cover_image_url=None,
        open_time=time(8, 0),
        close_time=time(18, 0),
    )

    created = run_async(business_service.create_business(data, owner_id, session))

    assert created.owner_id == owner_id
    assert session.commits == 1


def test_remove_business_marks_pending_as_deactivated() -> None:
    owner_id = uuid4()
    business = build_business(owner_id)
    session = FakeAsyncSession(exec_results=[business])

    run_async(business_service.remove_business(business.id, owner_id, session))

    assert business.status == ShopStatus.DEACTIVATED
    assert session.commits == 1


def test_remove_business_rejects_non_owner() -> None:
    business = build_business(uuid4())
    session = FakeAsyncSession(exec_results=[business])

    with pytest.raises(HTTPException) as exc:
        run_async(business_service.remove_business(business.id, uuid4(), session))

    assert exc.value.status_code == 401
