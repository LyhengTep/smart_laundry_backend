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


def build_notification() -> Notification:
    return Notification(
        id=uuid4(),
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
