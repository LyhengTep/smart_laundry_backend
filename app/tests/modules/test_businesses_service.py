from datetime import time
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.db.base  # noqa: F401
from app.modules.businesses import service as business_service
from app.modules.businesses.models import LaundryBusiness, ShopStatus
from app.modules.businesses.schema import BusinessWrite, ShopStatusAction, ShopStatusUpdate
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


# ===========================================================================
# toggle_shop_status
# exec_results order:
#   [0] = business lookup (.first())
#   [1] = active order count (.one())  — only when action=CLOSE without force
# ===========================================================================

def _build_toggleable_business(owner_id, status: ShopStatus = ShopStatus.OPEN) -> LaundryBusiness:
    b = build_business(owner_id)
    b.status = status
    return b


def test_close_open_shop_succeeds() -> None:
    owner_id = uuid4()
    business = _build_toggleable_business(owner_id, ShopStatus.OPEN)
    session = FakeAsyncSession(exec_results=[business, 0])

    result = run_async(
        business_service.toggle_shop_status(
            business_id=business.id,
            data=ShopStatusUpdate(action=ShopStatusAction.CLOSE),
            current_user=str(owner_id),
            session=session,
        )
    )

    assert result.status == ShopStatus.CLOSED.value
    assert session.commits == 1


def test_open_closed_shop_succeeds() -> None:
    owner_id = uuid4()
    business = _build_toggleable_business(owner_id, ShopStatus.CLOSED)
    session = FakeAsyncSession(exec_results=[business])

    result = run_async(
        business_service.toggle_shop_status(
            business_id=business.id,
            data=ShopStatusUpdate(action=ShopStatusAction.OPEN),
            current_user=str(owner_id),
            session=session,
        )
    )

    assert result.status == ShopStatus.OPEN.value
    assert session.commits == 1


def test_close_already_closed_returns_409() -> None:
    owner_id = uuid4()
    business = _build_toggleable_business(owner_id, ShopStatus.CLOSED)
    session = FakeAsyncSession(exec_results=[business])

    with pytest.raises(HTTPException) as exc:
        run_async(
            business_service.toggle_shop_status(
                business_id=business.id,
                data=ShopStatusUpdate(action=ShopStatusAction.CLOSE),
                current_user=str(owner_id),
                session=session,
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Shop is already closed"


def test_open_already_open_returns_409() -> None:
    owner_id = uuid4()
    business = _build_toggleable_business(owner_id, ShopStatus.OPEN)
    session = FakeAsyncSession(exec_results=[business])

    with pytest.raises(HTTPException) as exc:
        run_async(
            business_service.toggle_shop_status(
                business_id=business.id,
                data=ShopStatusUpdate(action=ShopStatusAction.OPEN),
                current_user=str(owner_id),
                session=session,
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Shop is already open"


def test_close_with_active_orders_returns_warning() -> None:
    owner_id = uuid4()
    business = _build_toggleable_business(owner_id, ShopStatus.OPEN)
    session = FakeAsyncSession(exec_results=[business, 3])

    result = run_async(
        business_service.toggle_shop_status(
            business_id=business.id,
            data=ShopStatusUpdate(action=ShopStatusAction.CLOSE, force=False),
            current_user=str(owner_id),
            session=session,
        )
    )

    assert result.active_order_count == 3
    assert result.warning is not None
    assert "3 active orders" in result.warning
    assert session.commits == 0


def test_close_with_active_orders_force_succeeds() -> None:
    owner_id = uuid4()
    business = _build_toggleable_business(owner_id, ShopStatus.OPEN)
    session = FakeAsyncSession(exec_results=[business])

    result = run_async(
        business_service.toggle_shop_status(
            business_id=business.id,
            data=ShopStatusUpdate(action=ShopStatusAction.CLOSE, force=True),
            current_user=str(owner_id),
            session=session,
        )
    )

    assert result.status == ShopStatus.CLOSED.value
    assert session.commits == 1


def test_toggle_shop_unauthorized_returns_403() -> None:
    business = _build_toggleable_business(uuid4(), ShopStatus.OPEN)
    session = FakeAsyncSession(exec_results=[business])

    with pytest.raises(HTTPException) as exc:
        run_async(
            business_service.toggle_shop_status(
                business_id=business.id,
                data=ShopStatusUpdate(action=ShopStatusAction.CLOSE),
                current_user=str(uuid4()),
                session=session,
            )
        )

    assert exc.value.status_code == 403


def test_toggle_shop_not_found_returns_404() -> None:
    session = FakeAsyncSession(exec_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(
            business_service.toggle_shop_status(
                business_id=uuid4(),
                data=ShopStatusUpdate(action=ShopStatusAction.CLOSE),
                current_user=str(uuid4()),
                session=session,
            )
        )

    assert exc.value.status_code == 404
