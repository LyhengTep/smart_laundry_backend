import re

from app.modules.orders.models import OrderStatus
from app.shared.common import (
    generate_order_no,
    get_assignment_room,
    get_notification_template,
    get_notification_title,
)


def test_generate_order_no_matches_expected_format() -> None:
    order_no = generate_order_no()
    assert re.match(r"^ORD-\d{14}-[A-F0-9]{6}$", order_no)


def test_generate_order_no_is_unique() -> None:
    nos = {generate_order_no() for _ in range(20)}
    assert len(nos) == 20


def test_get_assignment_room_formats_driver_id() -> None:
    room = get_assignment_room("driver-123")
    assert room == "assignment:driver-123"


def test_get_notification_template_cancelled() -> None:
    msg = get_notification_template(OrderStatus.CANCELLED, order_no="ORD-001")
    assert "ORD-001" in msg
    assert "cancelled" in msg.lower()


def test_get_notification_template_delivered_to_shop() -> None:
    msg = get_notification_template(OrderStatus.DELIVERED_TO_SHOP, order_no="ORD-002")
    assert "ORD-002" in msg
    assert "shop" in msg.lower()


def test_get_notification_template_unknown_status_returns_fallback() -> None:
    msg = get_notification_template(OrderStatus.PENDING, order_no="ORD-003")
    assert isinstance(msg, str)


def test_get_notification_title_cancelled() -> None:
    title = get_notification_title(OrderStatus.CANCELLED)
    assert "cancel" in title.lower()


def test_get_notification_title_delivered_to_shop() -> None:
    title = get_notification_title(OrderStatus.DELIVERED_TO_SHOP)
    assert isinstance(title, str)
    assert len(title) > 0


def test_get_notification_title_unknown_status_returns_fallback() -> None:
    title = get_notification_title(OrderStatus.PENDING)
    assert isinstance(title, str)
