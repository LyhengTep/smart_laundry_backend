from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.db.base  # noqa: F401
from app.modules.orders.models import Order, OrderStatus, PickupMethod
from app.modules.reviews import service as review_service
from app.modules.reviews.models import ShopReview
from app.modules.reviews.schema import ShopReviewCreate, ShopReviewUpdate
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_order(customer_id=None, business_id=None, status: OrderStatus = OrderStatus.DELIVERED) -> Order:
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


def build_review(customer_id=None, business_id=None) -> ShopReview:
    now = datetime.now(timezone.utc)
    return ShopReview(
        id=uuid4(),
        business_id=business_id or uuid4(),
        customer_id=customer_id or uuid4(),
        rating=4,
        comment="Great service",
        created_at=now,
        updated_at=now,
    )


# ===========================================================================
# Story 1: Customer Leaves a Review
# exec_results[0] = completed order query (.first())
# exec_results[1] = get_by_business_and_customer query (.first())
# ===========================================================================

def test_create_review_succeeds_for_completed_order() -> None:
    customer_id = uuid4()
    business_id = uuid4()
    order = build_order(customer_id=customer_id, business_id=business_id, status=OrderStatus.DELIVERED)

    session = FakeAsyncSession(exec_results=[order, None])

    data = ShopReviewCreate(rating=5, comment="Excellent!")
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


def test_create_review_rejects_no_completed_order() -> None:
    session = FakeAsyncSession(exec_results=[None])

    data = ShopReviewCreate(rating=4)
    with pytest.raises(HTTPException) as exc:
        run_async(
            review_service.create_review(
                business_id=uuid4(),
                customer_id=uuid4(),
                data=data,
                session=session,
            )
        )

    assert exc.value.status_code == 400


def test_create_review_rejects_already_reviewed() -> None:
    customer_id = uuid4()
    business_id = uuid4()
    order = build_order(customer_id=customer_id, business_id=business_id)
    existing = build_review(customer_id=customer_id, business_id=business_id)

    session = FakeAsyncSession(exec_results=[order, existing])

    data = ShopReviewCreate(rating=3)
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


def test_create_review_rejects_rating_below_1() -> None:
    with pytest.raises(Exception):
        ShopReviewCreate(rating=0)


def test_create_review_rejects_rating_above_5() -> None:
    with pytest.raises(Exception):
        ShopReviewCreate(rating=6)


# ===========================================================================
# Story 2: Customer Edits Their Review
# ===========================================================================

def test_update_review_succeeds() -> None:
    customer_id = uuid4()
    review = build_review(customer_id=customer_id)

    session = FakeAsyncSession(get_results=[review])
    data = ShopReviewUpdate(rating=2, comment="Changed my mind")

    result = run_async(
        review_service.update_review(
            review_id=review.id,
            customer_id=customer_id,
            data=data,
            session=session,
        )
    )

    assert result.rating == 2
    assert result.comment == "Changed my mind"
    assert session.commits == 1


def test_update_review_rejects_not_found() -> None:
    session = FakeAsyncSession(get_results=[None])
    data = ShopReviewUpdate(rating=3)

    with pytest.raises(HTTPException) as exc:
        run_async(
            review_service.update_review(
                review_id=uuid4(),
                customer_id=uuid4(),
                data=data,
                session=session,
            )
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "You have not reviewed this shop yet"


def test_update_review_rejects_wrong_customer() -> None:
    review = build_review(customer_id=uuid4())
    session = FakeAsyncSession(get_results=[review])
    data = ShopReviewUpdate(rating=1)

    with pytest.raises(HTTPException) as exc:
        run_async(
            review_service.update_review(
                review_id=review.id,
                customer_id=uuid4(),
                data=data,
                session=session,
            )
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "You are not authorized to edit this review"


def test_update_review_rejects_invalid_rating() -> None:
    with pytest.raises(Exception) as exc:
        ShopReviewUpdate(rating=0)
    assert "Rating must be between 1 and 5" in str(exc.value)

    with pytest.raises(Exception) as exc:
        ShopReviewUpdate(rating=6)
    assert "Rating must be between 1 and 5" in str(exc.value)


def test_update_review_rejects_empty_payload() -> None:
    with pytest.raises(Exception) as exc:
        ShopReviewUpdate()
    assert "At least one of rating or comment must be provided" in str(exc.value)
