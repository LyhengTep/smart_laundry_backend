from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.core.firebase import send_firebase_message, send_firebase_multicast
from app.exceptions.http import create_404
from app.modules.notifications.models import Notification, NotificationStatus
from app.modules.notifications.schema import (
    MulticastNotificationRequest,
    NotificationCreate,
    NotificationRead,
    PushNotificationRequest,
    PushNotificationResponse,
)
from app.modules.notifications import repository as repo
from app.shared.common import utc_now


async def list_notifications(
    session: AsyncSession,
    user_id: UUID | None = None,
    is_read: bool | None = None,
    status: NotificationStatus | None = None,
    reference_id: UUID | None = None,
    page: int = 1,
    size: int = 20,
) -> Page[NotificationRead]:
    return await repo.list_paginated(
        session,
        user_id=user_id,
        is_read=is_read,
        status=status,
        reference_id=reference_id,
        page=page,
        size=size,
    )


async def list_my_notifications(
    current_user_id: str,
    session: AsyncSession,
    is_read: bool | None = None,
    page: int = 1,
    size: int = 20,
) -> Page[NotificationRead]:
    return await repo.list_paginated(
        session,
        user_id=UUID(current_user_id),
        is_read=is_read,
        page=page,
        size=size,
    )


async def get_notification(notification_id: UUID, session: AsyncSession) -> NotificationRead:
    notification = await repo.get_by_id(notification_id, session)
    if notification is None:
        raise create_404("Notification not found")
    return notification


async def create_notification(data: NotificationCreate, session: AsyncSession) -> NotificationRead:
    notification = Notification(**data.model_dump())
    return await repo.save(notification, session)


async def mark_notification_as_read(notification_id: UUID, session: AsyncSession) -> NotificationRead:
    notification = await repo.get_by_id(notification_id, session)
    if notification is None:
        raise create_404("Notification not found")
    notification.is_read = True
    notification.read_at = utc_now()
    notification.status = NotificationStatus.READ
    return await repo.save(notification, session)


def send_push_notification(data: PushNotificationRequest) -> PushNotificationResponse:
    try:
        message_id = send_firebase_message(
            token=data.token,
            title=data.title,
            body=data.body,
            data=data.data,
        )
        return PushNotificationResponse(success=True, message_id=message_id)
    except Exception as exc:
        return PushNotificationResponse(success=False, error=str(exc))


def send_multicast_notification(data: MulticastNotificationRequest) -> PushNotificationResponse:
    try:
        result = send_firebase_multicast(
            tokens=data.tokens,
            title=data.title,
            body=data.body,
            data=data.data,
        )
        return PushNotificationResponse(
            success=result.failure_count == 0,
            message_id=f"success:{result.success_count}/failure:{result.failure_count}",
            error=None if result.failure_count == 0 else "Some notifications failed",
        )
    except Exception as exc:
        return PushNotificationResponse(success=False, error=str(exc))
