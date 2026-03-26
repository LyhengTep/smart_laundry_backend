from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.engine import get_session
from app.modules.notifications import service as svc
from app.modules.notifications.models import NotificationStatus
from app.modules.notifications.schema import (
    MulticastNotificationRequest,
    NotificationCreate,
    NotificationRead,
    PushNotificationRequest,
    PushNotificationResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationRead])
async def list_notifications(
    is_read: bool | None = Query(default=None),
    status: NotificationStatus | None = Query(default=None),
    reference_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationRead]:
    return await svc.list_notifications(
        session=session,
        is_read=is_read,
        status=status,
        reference_id=reference_id,
    )


@router.get("/{notification_id}", response_model=NotificationRead)
async def get_notification(notification_id: UUID, session: AsyncSession = Depends(get_session)) -> NotificationRead:
    return await svc.get_notification(notification_id=notification_id, session=session)


@router.post("/", response_model=NotificationRead)
async def create_notification(data: NotificationCreate, session: AsyncSession = Depends(get_session)) -> NotificationRead:
    return await svc.create_notification(data=data, session=session)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_as_read(
    notification_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> NotificationRead:
    return await svc.mark_notification_as_read(notification_id=notification_id, session=session)


@router.post("/push", response_model=PushNotificationResponse)
async def send_push_notification(data: PushNotificationRequest) -> PushNotificationResponse:
    return svc.send_push_notification(data)


@router.post("/push/multicast", response_model=PushNotificationResponse)
async def send_multicast_notification(data: MulticastNotificationRequest) -> PushNotificationResponse:
    return svc.send_multicast_notification(data)
