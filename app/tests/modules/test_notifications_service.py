from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.notifications import service as notification_service
from app.modules.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.modules.notifications.schema import (
    MulticastNotificationRequest,
    NotificationCreate,
    PushNotificationRequest,
)
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_notification(user_id=None) -> Notification:
    return Notification(
        id=uuid4(),
        user_id=user_id or uuid4(),
        type=NotificationType.ORDER_STATUS,
        title="Order created",
        message="A new order was created",
        reference_id=uuid4(),
        reference_type="ORDER",
        is_read=False,
        channel=NotificationChannel.IN_APP,
        status=NotificationStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        read_at=None,
    )


def test_create_notification_persists_notification() -> None:
    session = FakeAsyncSession()
    data = NotificationCreate(
        user_id=uuid4(),
        type=NotificationType.SYSTEM,
        title="General",
        message="System notification",
        reference_type="SYSTEM",
        channel=NotificationChannel.IN_APP,
        status=NotificationStatus.PENDING,
    )

    created = run_async(notification_service.create_notification(data, session))

    assert created.title == "General"
    assert session.commits == 1


def test_get_notification_raises_when_missing() -> None:
    session = FakeAsyncSession(get_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(notification_service.get_notification(uuid4(), session))

    assert exc.value.status_code == 404


def test_mark_notification_as_read_updates_flags() -> None:
    notification = build_notification()
    session = FakeAsyncSession(get_results=[notification])

    updated = run_async(notification_service.mark_notification_as_read(notification.id, session))

    assert updated.is_read is True
    assert updated.status == NotificationStatus.READ
    assert updated.read_at is not None


def test_list_notifications_filters_by_user_id() -> None:
    target_uid = uuid4()
    n1 = build_notification(user_id=target_uid)
    # exec_results: [0] count query, [1] items query
    session = FakeAsyncSession(exec_results=[1, [n1]])

    page = run_async(
        notification_service.list_notifications(session, user_id=target_uid)
    )

    assert page.total == 1
    assert len(page.items) == 1
    assert page.items[0].user_id == target_uid


def test_list_notifications_returns_pagination_metadata() -> None:
    notifications = [build_notification() for _ in range(3)]
    session = FakeAsyncSession(exec_results=[3, notifications[:2]])

    page = run_async(
        notification_service.list_notifications(session, page=1, size=2)
    )

    assert page.total == 3
    assert page.pages == 2
    assert page.size == 2
    assert len(page.items) == 2


def test_list_my_notifications_uses_current_user_id() -> None:
    uid = uuid4()
    notification = build_notification(user_id=uid)
    session = FakeAsyncSession(exec_results=[1, [notification]])

    page = run_async(
        notification_service.list_my_notifications(str(uid), session)
    )

    assert page.total == 1
    assert page.items[0].user_id == uid


def test_send_push_notification_returns_message_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notification_service, "send_firebase_message", lambda **_kwargs: "firebase-message-id")

    result = notification_service.send_push_notification(
        PushNotificationRequest(
            token="token-1",
            title="Hello",
            body="World",
            data={"order_id": "123"},
        )
    )

    assert result.success is True
    assert result.message_id == "firebase-message-id"


def test_send_multicast_notification_handles_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeBatchResponse:
        success_count = 1
        failure_count = 1

    monkeypatch.setattr(notification_service, "send_firebase_multicast", lambda **_kwargs: FakeBatchResponse())

    result = notification_service.send_multicast_notification(
        MulticastNotificationRequest(
            tokens=["a", "b"],
            title="Hello",
            body="World",
        )
    )

    assert result.success is False
    assert result.error == "Some notifications failed"
