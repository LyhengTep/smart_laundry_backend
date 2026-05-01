from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel

from app.modules.notifications.models import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)


class NotificationCreate(SQLModel):
    user_id: UUID
    type: NotificationType
    title: str
    message: str
    reference_id: UUID | None = None
    reference_type: str | None = None
    channel: NotificationChannel
    status: NotificationStatus = NotificationStatus.PENDING


class NotificationRead(SQLModel):
    id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    message: str
    reference_id: UUID | None
    reference_type: str | None
    is_read: bool
    channel: NotificationChannel
    status: NotificationStatus
    created_at: datetime
    read_at: datetime | None


class NotificationMarkRead(SQLModel):
    is_read: bool = True


class PushNotificationRequest(SQLModel):
    token: str
    title: str
    body: str
    data: dict[str, str] | None = None


class MulticastNotificationRequest(SQLModel):
    tokens: list[str]
    title: str
    body: str
    data: dict[str, str] | None = None


class PushNotificationResponse(SQLModel):
    success: bool
    message_id: str | None = None
    error: str | None = None
