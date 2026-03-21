from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.business_services.model import BusinessService, PriceType
from app.modules.laundry_services.model import LaundryService, ServiceEnum
from app.modules.orders.models import Order, OrderItem, OrderStatus, PickupMethod
from app.modules.orders.schema import OrderCreateItem, OrderPricingItemUpdate, OrderPricingUpdate
from app.modules.orders.service import (
    build_order_items,
    calculate_order_item_subtotal,
    calculate_order_total,
    generate_order_no,
    update_order_pricing,
    validate_status_transition,
)
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
        validate_status_transition(OrderStatus.PENDING, OrderStatus.WASHING)

    assert exc.value.status_code == 400


def test_validate_status_transition_allows_next_step() -> None:
    validate_status_transition(OrderStatus.READY_FOR_DELIVERY, OrderStatus.OUT_FOR_DELIVERY)


def test_generate_order_no_has_expected_prefix() -> None:
    assert generate_order_no().startswith("ORD-")


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
        total=7.5,
        created_at=now,
        updated_at=now,
        items=[item],
    )
    item.order_id = order.id
    return order, item


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
    session = FakeAsyncSession(exec_results=[order, order])
    data = OrderPricingUpdate(
        items=[OrderPricingItemUpdate(order_item_id=item.id, quantity=4.0)],
        discount=1.0,
    )

    updated = run_async(update_order_pricing(order.id, data, session))

    assert updated.subtotal == 10.0
    assert updated.total == 9.0
    assert updated.items[0].quantity == 4.0
