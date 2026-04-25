from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.db.base  # noqa: F401 - register SQLModel relationships for mapper initialization
from app.modules.payments import service as payment_service
from app.modules.payments.models import ConfirmedByType, CurrencyType, PaidByType, Payment, PaymentMethod, PaymentStatus, PaymentType
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
        type=PaymentType.WASHING_SERVICE_FEE,
    )

    created = run_async(payment_service.create_payment(data, session))

    assert created.order_id == order_id
    assert created.amount == Decimal("12.50")
    assert session.commits == 1


def test_create_payment_rejects_missing_order() -> None:
    session = FakeAsyncSession(get_results=[None])
    data = PaymentCreate(order_id=uuid4(), amount=Decimal("12.50"), paid_by=PaidByType.CUSTOMER, type=PaymentType.WASHING_SERVICE_FEE)

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


def test_collect_assignment_payments_marks_all_pending_collected() -> None:
    now = datetime.now(timezone.utc)
    assignment_id = uuid4()
    payments = [
        Payment(id=uuid4(), order_id=uuid4(), assignment_id=assignment_id, method=PaymentMethod.CASH,
                status=PaymentStatus.PENDING, amount=Decimal("10.00"), currency=CurrencyType.USD,
                paid_by=PaidByType.CUSTOMER, paid_at=now, created_at=now, updated_at=now,
                type=PaymentType.DELIVERY_FEE),
        Payment(id=uuid4(), order_id=uuid4(), assignment_id=assignment_id, method=PaymentMethod.CASH,
                status=PaymentStatus.PENDING, amount=Decimal("20.00"), currency=CurrencyType.USD,
                paid_by=PaidByType.CUSTOMER, paid_at=now, created_at=now, updated_at=now,
                type=PaymentType.WASHING_SERVICE_FEE),
    ]
    session = FakeAsyncSession(exec_results=[payments])

    run_async(payment_service.collect_assignment_payments(assignment_id, session))

    assert all(p.status == PaymentStatus.COLLECTED for p in payments)
    assert session.commits == 1


def test_collect_assignment_payments_no_op_when_none_pending() -> None:
    session = FakeAsyncSession(exec_results=[[]])

    run_async(payment_service.collect_assignment_payments(uuid4(), session))

    assert session.commits == 1
    assert session.added == []


def test_create_pending_settlement_payment_creates_correct_record() -> None:
    now = datetime.now(timezone.utc)
    existing = Payment(id=uuid4(), order_id=uuid4(), method=PaymentMethod.CASH, status=PaymentStatus.PENDING,
                       amount=Decimal("5.00"), currency=CurrencyType.USD, paid_by=PaidByType.CUSTOMER,
                       paid_at=now, created_at=now, updated_at=now)
    order_id = uuid4()
    session = FakeAsyncSession(exec_results=[existing])

    result = run_async(
        payment_service.create_pending_settlement_payment(
            order_id=order_id,
            assignment_id=uuid4(),
            amount=Decimal("15.00"),
            payment_type=PaymentType.PICKUP_FEE,
            session=session,
        )
    )

    assert result.status == PaymentStatus.PENDING_SETTLEMENT
    assert result.paid_by == PaidByType.SHOP
    assert result.type == PaymentType.PICKUP_FEE
    assert result.amount == Decimal("15.00")
    assert session.commits == 1


def test_settle_shop_advance_payment_settles_pending_and_creates_advance() -> None:
    now = datetime.now(timezone.utc)
    order_id = uuid4()
    assignment_id = uuid4()
    pending = Payment(
        id=uuid4(), order_id=order_id, assignment_id=assignment_id, method=PaymentMethod.CASH,
        status=PaymentStatus.PENDING_SETTLEMENT, amount=Decimal("12.00"), currency=CurrencyType.USD,
        paid_by=PaidByType.SHOP, paid_at=None, created_at=now, updated_at=now,
        type=PaymentType.PICKUP_FEE,
    )
    session = FakeAsyncSession(exec_results=[pending])

    settlement = run_async(
        payment_service.settle_shop_advance_payment(
            order_id=order_id,
            assignment_id=assignment_id,
            payment_type=PaymentType.PICKUP_FEE,
            session=session,
        )
    )

    assert settlement is not None
    assert settlement.status == PaymentStatus.COLLECTED
    assert settlement.type == PaymentType.ADVANCE_SETTLEMENT
    assert settlement.amount == Decimal("12.00")
    assert pending.status == PaymentStatus.SETTLED
    assert pending.settled_by_payment_id == settlement.id
    assert session.commits == 1


def test_settle_shop_advance_payment_returns_none_when_no_pending() -> None:
    session = FakeAsyncSession(exec_results=[None])

    result = run_async(
        payment_service.settle_shop_advance_payment(
            order_id=uuid4(),
            assignment_id=uuid4(),
            payment_type=PaymentType.PICKUP_FEE,
            session=session,
        )
    )

    assert result is None


def test_get_driver_revenue_returns_sum_of_collected_payments() -> None:
    driver_id = uuid4()
    session = FakeAsyncSession(exec_results=[Decimal("150.00")])

    result = run_async(payment_service.get_driver_revenue(driver_id, session))

    assert result.driver_id == driver_id
    assert result.total_revenue == Decimal("150.00")
    assert result.currency == CurrencyType.USD


def test_get_driver_revenue_returns_zero_when_no_payments() -> None:
    driver_id = uuid4()
    session = FakeAsyncSession(exec_results=[Decimal("0")])

    result = run_async(payment_service.get_driver_revenue(driver_id, session))

    assert result.total_revenue == Decimal("0")


def test_get_business_revenue_returns_sum_of_washing_service_fees() -> None:
    business_id = uuid4()
    session = FakeAsyncSession(exec_results=[Decimal("300.00")])

    result = run_async(payment_service.get_business_revenue(business_id, session))

    assert result.business_id == business_id
    assert result.total_revenue == Decimal("300.00")
    assert result.currency == CurrencyType.USD


def test_get_business_revenue_returns_zero_when_no_orders() -> None:
    business_id = uuid4()
    session = FakeAsyncSession(exec_results=[Decimal("0")])

    result = run_async(payment_service.get_business_revenue(business_id, session))

    assert result.total_revenue == Decimal("0")
