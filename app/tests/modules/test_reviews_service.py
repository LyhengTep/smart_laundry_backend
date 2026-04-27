from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.db.base  # noqa: F401
from app.modules.orders.models import Order, OrderStatus, PickupMethod, DeliveryFeePaidBy
from app.modules.reviews import service as review_service
from app.modules.reviews.models import ShopReview
from app.modules.reviews.schema import ShopReviewCreate
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_order(
    customer_id=None,
    business_id=None,
    status: OrderStatus = OrderStatus.DELIVERED,
) -> Order:
    now = datetime.now(timezone.utc)
    return Order(
        id=uuid4(),
        order_no="ORD-TEST-001",
        customer_id=customer_id or uuid4(),
        business_id=business_id or uuid4(),
        pickup_method=PickupMethod.PICKUP,
        pickup_address="123 St",
        delivery_address="456 St",
        pickup_latitude=0.0,
        pickup_longitude=0.0,
        delivery_latitude=0.0,
        delivery_longitude=0.0,
        status=status,
        subtotal=0.0,
        discount=0.0,
        delivery_fee=0.0,
        pickup_fee=0.0,
        total=0.0,
        placed_at=now,
        created_at=now,
        updated_at=now,
    )


def build_review(customer_id=None, business_id=None, order_id=None) -> ShopReview:
    now = datetime.now(timezone.utc)
    return ShopReview(
        id=uuid4(),
        business_id=business_id or uuid4(),
        customer_id=customer_id or uuid4(),
        order_id=order_id or uuid4(),
        rating=4,
        comment="Great service",
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_create_review_succeeds_for_completed_order() -> None:
    customer_id = uuid4()
    business_id = uuid4()
    order = build_order(customer_id=customer_id, business_id=business_id, status=OrderStatus.DELIVERED)

    session = FakeAsyncSession(
        get_results=[order],           # session.get(Order, order_id)
        exec_results=[None],           # get_by_order_id → no existing review
    )

    data = ShopReviewCreate(order_id=order.id, rating=5, comment="Excellent!")
    result = run_async(
        review_service.create_review(
            business_id=business_id,
            customer_id=customer_id,
            data=data,
            session=session,
        )
    )

    assert result.rating == 5
    assert result.comment == "Excellent!"
    assert result.business_id == business_id
    assert result.customer_id == customer_id
    assert session.commits == 1


# ---------------------------------------------------------------------------
# Already reviewed
# ---------------------------------------------------------------------------

def test_create_review_rejects_duplicate_order_review() -> None:
    customer_id = uuid4()
    business_id = uuid4()
    order = build_order(customer_id=customer_id, business_id=business_id, status=OrderStatus.DELIVERED)
    existing_review = build_review(customer_id=customer_id, business_id=business_id, order_id=order.id)

    session = FakeAsyncSession(
        get_results=[order],
        exec_results=[existing_review],   # get_by_order_id → already exists
    )

    data = ShopReviewCreate(order_id=order.id, rating=3)
    with pytest.raises(HTTPException) as exc:
        run_async(
            review_service.create_review(
                business_id=business_id,
                customer_id=customer_id,
                data=data,
                session=session,
            )
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Order not completed
# ---------------------------------------------------------------------------

def test_create_review_rejects_non_completed_order() -> None:
    customer_id = uuid4()
    business_id = uuid4()
    order = build_order(customer_id=customer_id, business_id=business_id, status=OrderStatus.PROCESSING)

    session = FakeAsyncSession(get_results=[order], exec_results=[])

    data = ShopReviewCreate(order_id=order.id, rating=4)
    with pytest.raises(HTTPException) as exc:
        run_async(
            review_service.create_review(
                business_id=business_id,
                customer_id=customer_id,
                data=data,
                session=session,
            )
        )

    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# Invalid rating (schema-level validation)
# ---------------------------------------------------------------------------

def test_create_review_rejects_rating_below_1() -> None:
    with pytest.raises(Exception):
        ShopReviewCreate(order_id=uuid4(), rating=0)


def test_create_review_rejects_rating_above_5() -> None:
    with pytest.raises(Exception):
        ShopReviewCreate(order_id=uuid4(), rating=6)


# ---------------------------------------------------------------------------
# Order does not belong to this customer
# ---------------------------------------------------------------------------

def test_create_review_rejects_wrong_customer() -> None:
    business_id = uuid4()
    order = build_order(customer_id=uuid4(), business_id=business_id, status=OrderStatus.DELIVERED)
    different_customer = uuid4()

    session = FakeAsyncSession(get_results=[order], exec_results=[])

    data = ShopReviewCreate(order_id=order.id, rating=4)
    with pytest.raises(HTTPException) as exc:
        run_async(
            review_service.create_review(
                business_id=business_id,
                customer_id=different_customer,
                data=data,
                session=session,
            )
        )

    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# Order does not belong to this shop
# ---------------------------------------------------------------------------

def test_create_review_rejects_wrong_business() -> None:
    customer_id = uuid4()
    order = build_order(customer_id=customer_id, business_id=uuid4(), status=OrderStatus.DELIVERED)
    different_business = uuid4()

    session = FakeAsyncSession(get_results=[order], exec_results=[])

    data = ShopReviewCreate(order_id=order.id, rating=4)
    with pytest.raises(HTTPException) as exc:
        run_async(
            review_service.create_review(
                business_id=different_business,
                customer_id=customer_id,
                data=data,
                session=session,
            )
        )

    assert exc.value.status_code == 400
