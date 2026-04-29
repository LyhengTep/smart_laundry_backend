from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.business_services.model import BusinessService, PriceType
from app.modules.laundry_services.model import LaundryService, ServiceEnum
from app.modules.orders.models import DeliveryFeePaidBy, Order, OrderItem, OrderStatus, PickupMethod
from app.modules.orders.schema import (
    OrderCreate,
    OrderCreateItem,
    OrderPricingItemUpdate,
    OrderPricingUpdate,
    OrderStatusUpdate,
)
from app.modules.orders import service as order_service
from app.modules.orders.service import (
    build_order_event_payload,
    build_order_items,
    calculate_order_item_subtotal,
    calculate_order_total,
    update_order_status,
    update_order_pricing,
    validate_status_transition,
    mark_order_payment_received,
)
from app.shared.common import generate_order_no
from app.modules.payments.models import CurrencyType, PaidByType, Payment, PaymentMethod, PaymentStatus
from app.modules.users.models import RoleName, User, UserStatus
from app.tests.modules.conftest import FakeAsyncSession, run_async


def test_calculate_order_item_subtotal_rejects_non_positive_quantity() -> None:
    with pytest.raises(HTTPException) as exc:
        calculate_order_item_subtotal(unit_price=3.5, quantity=0)

    assert exc.value.status_code == 400


def test_build_order_items_creates_snapshot_and_total() -> None:
    business_service_id = uuid4()
    laundry_service = LaundryService(
        id=1,
        name=ServiceEnum.WASH,
        code="WASH",
        description="Wash service",
    )
    business_service = BusinessService(
        id=business_service_id,
        business_id=uuid4(),
        service_id=laundry_service.id,
        base_price=2.5,
        pricing_type=PriceType.PER_WEIGHT,
        laundry_service=laundry_service,
    )

    order_items, total = build_order_items(
        items_data=[OrderCreateItem(business_service_id=business_service_id, quantity=4)],
        business_services_by_id={business_service_id: business_service},
    )

    assert len(order_items) == 1
    assert order_items[0].service_name == "WASH"
    assert order_items[0].measure_type == "kg"
    assert order_items[0].sub_total == 10.0
    assert total == 10.0
    assert calculate_order_total([item.sub_total for item in order_items]) == 10.0


def test_build_order_items_rejects_duplicate_business_service() -> None:
    business_service_id = uuid4()
    laundry_service = LaundryService(
        id=2,
        name=ServiceEnum.IRON,
        code="IRON",
        description="Iron service",
    )
    business_service = BusinessService(
        id=business_service_id,
        business_id=uuid4(),
        service_id=laundry_service.id,
        base_price=1.25,
        pricing_type=PriceType.PER_ITEM,
        laundry_service=laundry_service,
    )

    with pytest.raises(HTTPException) as exc:
        build_order_items(
            items_data=[
                OrderCreateItem(business_service_id=business_service_id, quantity=1),
                OrderCreateItem(business_service_id=business_service_id, quantity=2),
            ],
            business_services_by_id={business_service_id: business_service},
        )

    assert exc.value.status_code == 400


def test_validate_status_transition_rejects_skipped_state() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_status_transition(OrderStatus.PENDING, OrderStatus.PROCESSING)

    assert exc.value.status_code == 400


def test_validate_status_transition_allows_next_step() -> None:
    validate_status_transition(OrderStatus.READY_FOR_DELIVERY, OrderStatus.DELIVERY_ASSIGNED)


def test_generate_order_no_has_expected_prefix() -> None:
    assert generate_order_no().startswith("ORD-")


def test_build_order_event_payload_contains_expected_fields() -> None:
    now = datetime.now(timezone.utc)
    order = Order(
        id=uuid4(),
        order_no="ORD-001",
        customer_id=uuid4(),
        business_id=uuid4(),
        driver_id=None,
        status=OrderStatus.PENDING,
        pickup_method=PickupMethod.PICKUP,
        placed_at=now,
        pickup_address="Pickup",
        pickup_latitude=1.0,
        pickup_longitude=2.0,
        delivery_address="Delivery",
        delivery_latitude=3.0,
        delivery_longitude=4.0,
        notes=None,
        subtotal=7.5,
        discount=0,
        delivery_fee=0,
        delivery_fee_paid_by=DeliveryFeePaidBy.CUSTOMER,
        total=7.5,
        created_at=now,
        updated_at=now,
        items=[],
    )

    payload = build_order_event_payload("order_status_updated", order)

    assert payload["event"] == "order_status_updated"
    assert payload["order_id"] == str(order.id)
    assert payload["customer_id"] == str(order.customer_id)
    assert payload["status"] == OrderStatus.PENDING.value


def test_create_order_creates_pending_customer_payment(monkeypatch: pytest.MonkeyPatch) -> None:
    customer = build_user()
    business_id = uuid4()
    business_service_id = uuid4()
    laundry_service = LaundryService(
        id=3,
        name=ServiceEnum.WASH,
        code="WASH-PAY",
        description="Wash payment test",
    )
    business_service = BusinessService(
        id=business_service_id,
        business_id=business_id,
        service_id=laundry_service.id,
        base_price=5.0,
        pricing_type=PriceType.PER_ITEM,
        laundry_service=laundry_service,
    )
    created_order = Order(
        id=uuid4(),
        order_no="ORD-PAYMENT",
        customer_id=customer.id,
        business_id=business_id,
        driver_id=None,
        status=OrderStatus.PENDING,
        pickup_method=PickupMethod.PICKUP,
        pickup_address="Pickup",
        pickup_latitude=1.0,
        pickup_longitude=2.0,
        delivery_address="Delivery",
        delivery_latitude=3.0,
        delivery_longitude=4.0,
        notes=None,
        subtotal=10.0,
        discount=1.0,
        delivery_fee=0,
        delivery_fee_paid_by=DeliveryFeePaidBy.SHOP,
        total=9.0,
        items=[],
    )
    session = FakeAsyncSession(
        get_results=[customer, object()],
        exec_results=[[business_service], created_order],
    )

    async def fake_broadcast(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(order_service, "broadcast_order_event", fake_broadcast)

    result = run_async(
        order_service.create_order(
            session=session,
            data=OrderCreate(
                customer_id=customer.id,
                business_id=business_id,
                pickup_method=PickupMethod.PICKUP,
                payment_method=PaymentMethod.CASH,
                payment_currency=CurrencyType.USD,
                delivery_fee_paid_by=DeliveryFeePaidBy.SHOP,
                pickup_address="Pickup",
                delivery_address="Delivery",
                discount=1.0,
                pickup_latitude=1.0,
                pickup_longitude=2.0,
                delivery_latitude=3.0,
                delivery_longitude=4.0,
                items=[OrderCreateItem(business_service_id=business_service_id, quantity=2)],
            ),
        )
    )

    payment = next(item for item in session.added if isinstance(item, Payment))
    assert result == created_order
    assert payment.order_id == session.added[0].id
    assert payment.amount == Decimal("9.0")
    assert payment.method == PaymentMethod.CASH
    assert payment.status == PaymentStatus.PENDING
    assert payment.currency == CurrencyType.USD
    assert payment.paid_by == PaidByType.CUSTOMER
    assert session.added[0].delivery_fee == 0
    assert session.added[0].delivery_fee_paid_by == DeliveryFeePaidBy.SHOP
    assert session.commits == 1


def test_calculate_order_total_applies_discount() -> None:
    assert calculate_order_total([10.0, 5.0], 3.0) == 12.0


def test_calculate_order_total_rejects_excessive_discount() -> None:
    with pytest.raises(HTTPException) as exc:
        calculate_order_total([10.0], 11.0)

    assert exc.value.status_code == 400


def build_order_for_pricing(status: OrderStatus) -> tuple[Order, OrderItem]:
    now = datetime.now(timezone.utc)
    item = OrderItem(
        id=uuid4(),
        order_id=uuid4(),
        business_service_id=uuid4(),
        service_id=1,
        service_name="WASH",
        pricing_type=PriceType.PER_WEIGHT,
        qty=3.0,
        measure_type="kg",
        unit_price=2.5,
        quantity=3.0,
        sub_total=7.5,
        note=None,
    )
    order = Order(
        id=uuid4(),
        order_no="ORD-PRICE",
        customer_id=uuid4(),
        business_id=uuid4(),
        driver_id=None,
        status=status,
        pickup_method=PickupMethod.PICKUP,
        placed_at=now,
        pickup_address="Pickup",
        pickup_latitude=1.0,
        pickup_longitude=2.0,
        delivery_address="Delivery",
        delivery_latitude=3.0,
        delivery_longitude=4.0,
        notes=None,
        subtotal=7.5,
        discount=0,
        delivery_fee=0,
        delivery_fee_paid_by=DeliveryFeePaidBy.CUSTOMER,
        total=7.5,
        created_at=now,
        updated_at=now,
        items=[item],
    )
    item.order_id = order.id
    return order, item


def build_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        full_name="Order User",
        user_name="order-user",
        email="order@example.com",
        phone=None,
        msg_token="firebase-token",
        password_hash="hashed",
        role=RoleName.CUSTOMER,
        status=UserStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_update_order_status_updates_status_and_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    order, _ = build_order_for_pricing(OrderStatus.CONFIRMED)
    driver_id = uuid4()
    session = FakeAsyncSession(exec_results=[order, order])
    broadcast_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(order_service, "utc_now", lambda: datetime(2026, 3, 27, tzinfo=timezone.utc))

    async def fake_broadcast(event: str, updated_order: Order) -> None:
        broadcast_calls.append((event, str(updated_order.id)))

    monkeypatch.setattr(order_service, "broadcast_order_event", fake_broadcast)

    updated = run_async(
        update_order_status(
            order.id,
            OrderStatusUpdate(status=OrderStatus.PICKUP_ASSIGNED, driver_id=driver_id),
            session,
        )
    )

    assert updated.status == OrderStatus.PICKUP_ASSIGNED
    assert updated.driver_id == driver_id
    assert session.commits == 1
    assert broadcast_calls == [("order_status_updated", str(order.id))]


def test_update_order_status_rejects_invalid_transition() -> None:
    order, _ = build_order_for_pricing(OrderStatus.PENDING)
    session = FakeAsyncSession(exec_results=[order])

    with pytest.raises(HTTPException) as exc:
        run_async(
            update_order_status(
                order.id,
                OrderStatusUpdate(status=OrderStatus.PROCESSING),
                session,
            )
        )

    assert exc.value.status_code == 400


def test_update_order_status_confirmed_can_set_delivery_fee(monkeypatch: pytest.MonkeyPatch) -> None:
    order, _ = build_order_for_pricing(OrderStatus.PENDING)
    payment = Payment(
        order_id=order.id,
        method=PaymentMethod.CASH,
        status=PaymentStatus.PENDING,
        amount=Decimal("7.5"),
        currency=CurrencyType.USD,
        paid_by=PaidByType.CUSTOMER,
        paid_at=datetime.now(timezone.utc),
    )
    session = FakeAsyncSession(exec_results=[order, [payment], order])
    monkeypatch.setattr(order_service, "broadcast_order_event", AsyncMock())

    updated = run_async(
        update_order_status(
            order.id,
            OrderStatusUpdate(status=OrderStatus.CONFIRMED, pickup_fee=2.0),
            session,
        )
    )

    assert updated.status == OrderStatus.CONFIRMED
    assert updated.pickup_fee == 2.0
    assert updated.delivery_fee == 2.0
    assert updated.total == 11.5
    assert payment.amount == Decimal("11.5")
    assert session.commits == 1


def test_update_order_status_pickup_sets_payer_to_shop() -> None:
    order, _ = build_order_for_pricing(OrderStatus.PICKUP_ASSIGNED)
    session = FakeAsyncSession(exec_results=[order, order])

    updated = run_async(
        update_order_status(
            order.id,
            OrderStatusUpdate(
                status=OrderStatus.PICKED_UP,
                delivery_fee_paid_by=DeliveryFeePaidBy.SHOP,
            ),
            session,
        )
    )

    assert updated.status == OrderStatus.PICKED_UP
    assert updated.delivery_fee_paid_by == DeliveryFeePaidBy.SHOP
    assert updated.delivery_fee == 0
    assert session.commits == 1


def test_update_order_status_rejects_delivery_fee_at_pickup() -> None:
    order, _ = build_order_for_pricing(OrderStatus.PICKUP_ASSIGNED)
    session = FakeAsyncSession(exec_results=[order])

    with pytest.raises(HTTPException) as exc:
        run_async(
            update_order_status(
                order.id,
                OrderStatusUpdate(status=OrderStatus.PICKED_UP, pickup_fee=3.0),
                session,
            )
        )

    assert exc.value.status_code == 400
    assert "when confirming" in exc.value.detail


def test_update_order_status_pickup_without_fee_leaves_existing_values() -> None:
    order, _ = build_order_for_pricing(OrderStatus.PICKUP_ASSIGNED)
    session = FakeAsyncSession(exec_results=[order, order])

    updated = run_async(
        update_order_status(
            order.id,
            OrderStatusUpdate(status=OrderStatus.PICKED_UP),
            session,
        )
    )

    assert updated.status == OrderStatus.PICKED_UP
    assert updated.delivery_fee == 0
    assert updated.delivery_fee_paid_by == DeliveryFeePaidBy.CUSTOMER


def test_update_order_status_rejects_delivery_fee_payer_outside_pickup() -> None:
    order, _ = build_order_for_pricing(OrderStatus.PENDING)
    session = FakeAsyncSession(exec_results=[order])

    with pytest.raises(HTTPException) as exc:
        run_async(
            update_order_status(
                order.id,
                OrderStatusUpdate(
                    status=OrderStatus.CONFIRMED,
                    delivery_fee_paid_by=DeliveryFeePaidBy.SHOP,
                ),
                session,
            )
        )

    assert exc.value.status_code == 400
    assert "at pickup" in exc.value.detail


def test_update_order_status_rejects_delivery_fee_outside_confirmation() -> None:
    order, _ = build_order_for_pricing(OrderStatus.CONFIRMED)
    session = FakeAsyncSession(exec_results=[order])

    with pytest.raises(HTTPException) as exc:
        run_async(
            update_order_status(
                order.id,
                OrderStatusUpdate(status=OrderStatus.PICKUP_ASSIGNED, pickup_fee=2.0),
                session,
            )
        )

    assert exc.value.status_code == 400
    assert "when confirming" in exc.value.detail


def test_update_order_status_cancelled_sends_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    order, _ = build_order_for_pricing(OrderStatus.PENDING)
    session = FakeAsyncSession(exec_results=[order, order])
    broadcast_calls: list[str] = []

    async def fake_broadcast(event: str, updated_order: Order) -> None:
        broadcast_calls.append(event)

    monkeypatch.setattr(order_service, "broadcast_order_event", fake_broadcast)

    updated = run_async(
        update_order_status(
            order.id,
            OrderStatusUpdate(status=OrderStatus.CANCELLED),
            session,
        )
    )

    assert updated.status == OrderStatus.CANCELLED
    assert session.commits == 1
    assert broadcast_calls == ["order_status_updated"]


def test_update_order_status_delivery_pickup_sets_payer(monkeypatch: pytest.MonkeyPatch) -> None:
    order, _ = build_order_for_pricing(OrderStatus.OUT_FOR_DELIVERY)
    session = FakeAsyncSession(exec_results=[order, order])
    monkeypatch.setattr(order_service, "broadcast_order_event", AsyncMock())

    updated = run_async(
        update_order_status(
            order.id,
            OrderStatusUpdate(
                status=OrderStatus.PICKED_UP_DELIVERY,
                delivery_fee_paid_by=DeliveryFeePaidBy.SHOP,
            ),
            session,
        )
    )

    assert updated.status == OrderStatus.PICKED_UP_DELIVERY
    assert updated.delivery_fee_paid_by == DeliveryFeePaidBy.SHOP
    assert session.commits == 1


def test_update_order_status_delivered_to_shop_marks_payment_received() -> None:
    order, _ = build_order_for_pricing(OrderStatus.PICKED_UP)
    payment = Payment(
        order_id=order.id,
        method=PaymentMethod.CASH,
        status=PaymentStatus.PENDING,
        amount=Decimal("7.5"),
        currency=CurrencyType.USD,
        paid_by=PaidByType.CUSTOMER,
        paid_at=datetime.now(timezone.utc),
    )
    session = FakeAsyncSession(exec_results=[order, [payment], order])

    updated = run_async(
        update_order_status(
            order.id,
            OrderStatusUpdate(status=OrderStatus.DELIVERED_TO_SHOP),
            session,
        )
    )

    assert updated.status == OrderStatus.DELIVERED_TO_SHOP
    assert payment.status == PaymentStatus.COLLECTED
    assert session.commits == 1


def test_update_order_status_delivered_to_shop_no_payment_is_noop() -> None:
    order, _ = build_order_for_pricing(OrderStatus.PICKED_UP)
    session = FakeAsyncSession(exec_results=[order, [], order])

    updated = run_async(
        update_order_status(
            order.id,
            OrderStatusUpdate(status=OrderStatus.DELIVERED_TO_SHOP),
            session,
        )
    )

    assert updated.status == OrderStatus.DELIVERED_TO_SHOP
    assert session.commits == 1


def test_update_order_pricing_rejects_before_shop_delivery() -> None:
    order, item = build_order_for_pricing(OrderStatus.PICKED_UP)
    session = FakeAsyncSession(exec_results=[order])
    data = OrderPricingUpdate(
        items=[OrderPricingItemUpdate(order_item_id=item.id, quantity=4.0)],
        discount=0,
    )

    with pytest.raises(HTTPException) as exc:
        run_async(update_order_pricing(order.id, data, session))

    assert exc.value.status_code == 400
    assert "after delivery to the shop" in exc.value.detail


def test_update_order_pricing_recalculates_after_shop_delivery() -> None:
    order, item = build_order_for_pricing(OrderStatus.DELIVERED_TO_SHOP)
    session = FakeAsyncSession(exec_results=[order, [], order])
    data = OrderPricingUpdate(
        items=[OrderPricingItemUpdate(order_item_id=item.id, quantity=4.0)],
        discount=1.0,
        delivery_fee=2.0,
    )

    updated = run_async(update_order_pricing(order.id, data, session))

    assert updated.subtotal == 10.0
    assert updated.delivery_fee == 2.0
    assert updated.total == 11.0
    assert updated.items[0].quantity == 4.0


def test_update_order_pricing_updates_pending_customer_payment_amount() -> None:
    order, item = build_order_for_pricing(OrderStatus.DELIVERED_TO_SHOP)
    payment = Payment(
        order_id=order.id,
        method=PaymentMethod.CASH,
        status=PaymentStatus.PENDING,
        amount=Decimal("7.5"),
        currency=CurrencyType.USD,
        paid_by=PaidByType.CUSTOMER,
        paid_at=datetime.now(timezone.utc),
    )
    session = FakeAsyncSession(exec_results=[order, [payment], order])
    data = OrderPricingUpdate(
        items=[OrderPricingItemUpdate(order_item_id=item.id, quantity=4.0)],
        discount=1.0,
        delivery_fee=2.0,
    )

    run_async(update_order_pricing(order.id, data, session))

    assert payment.amount == Decimal("11.0")
