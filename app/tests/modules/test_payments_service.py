from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.db.base  # noqa: F401 - register SQLModel relationships for mapper initialization
from app.modules.payments import service as payment_service
from app.modules.payments.models import ConfirmedByType, CurrencyType, PaidByType, Payment, PaymentMethod, PaymentStatus
from app.modules.payments.schema import PaymentConfirm, PaymentCreate, PaymentUpdate
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_payment() -> Payment:
    now = datetime.now(timezone.utc)
    return Payment(
        id=uuid4(),
        order_id=uuid4(),
        method=PaymentMethod.CASH,
        status=PaymentStatus.PENDING,
        amount=Decimal("10.00"),
        currency=CurrencyType.USD,
        provider_ref=None,
        paid_by=PaidByType.CUSTOMER,
        paid_at=now,
        created_at=now,
        updated_at=now,
    )


def test_create_payment_persists_payment() -> None:
    order_id = uuid4()
    session = FakeAsyncSession(get_results=[object()])
    data = PaymentCreate(
        order_id=order_id,
        amount=Decimal("12.50"),
        paid_by=PaidByType.CUSTOMER,
    )

    created = run_async(payment_service.create_payment(data, session))

    assert created.order_id == order_id
    assert created.amount == Decimal("12.50")
    assert session.commits == 1


def test_create_payment_rejects_missing_order() -> None:
    session = FakeAsyncSession(get_results=[None])
    data = PaymentCreate(order_id=uuid4(), amount=Decimal("12.50"), paid_by=PaidByType.CUSTOMER)

    with pytest.raises(HTTPException) as exc:
        run_async(payment_service.create_payment(data, session))

    assert exc.value.status_code == 404


def test_update_payment_updates_fields() -> None:
    payment = build_payment()
    session = FakeAsyncSession(get_results=[payment])

    updated = run_async(
        payment_service.update_payment(
            payment.id,
            PaymentUpdate(status=PaymentStatus.COLLECTED, provider_ref="TXN-1"),
            session,
        )
    )

    assert updated.status == PaymentStatus.COLLECTED
    assert updated.provider_ref == "TXN-1"
    assert session.commits == 1


def test_delete_payment_deletes_payment() -> None:
    payment = build_payment()
    session = FakeAsyncSession(get_results=[payment])

    result = run_async(payment_service.delete_payment(payment.id, session))

    assert result is True
    assert session.deleted == [payment]
    assert session.commits == 1


def test_confirm_payment_marks_success_and_sets_confirmed_by() -> None:
    payment = build_payment()
    session = FakeAsyncSession(get_results=[payment])

    confirmed = run_async(
        payment_service.confirm_payment(
            payment.id,
            PaymentConfirm(confirmed_by=ConfirmedByType.DRIVER),
            session,
        )
    )

    assert confirmed.status == PaymentStatus.COLLECTED
    assert confirmed.confirmed_by == ConfirmedByType.DRIVER
    assert session.commits == 1


def test_confirm_payment_by_admin_sets_confirmed_by_admin() -> None:
    payment = build_payment()
    session = FakeAsyncSession(get_results=[payment])

    confirmed = run_async(
        payment_service.confirm_payment(
            payment.id,
            PaymentConfirm(confirmed_by=ConfirmedByType.ADMIN),
            session,
        )
    )

    assert confirmed.status == PaymentStatus.COLLECTED
    assert confirmed.confirmed_by == ConfirmedByType.ADMIN


def test_confirm_payment_rejects_already_confirmed() -> None:
    payment = build_payment()
    payment.status = PaymentStatus.COLLECTED
    session = FakeAsyncSession(get_results=[payment])

    with pytest.raises(HTTPException) as exc:
        run_async(
            payment_service.confirm_payment(
                payment.id,
                PaymentConfirm(confirmed_by=ConfirmedByType.DRIVER),
                session,
            )
        )

    assert exc.value.status_code == 400


def test_confirm_payment_rejects_missing_payment() -> None:
    session = FakeAsyncSession(get_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(
            payment_service.confirm_payment(
                uuid4(),
                PaymentConfirm(confirmed_by=ConfirmedByType.ADMIN),
                session,
            )
        )

    assert exc.value.status_code == 404
