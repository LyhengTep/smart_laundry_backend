from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.db.engine import get_session
from app.lib.security import get_current_user
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


@router.get("/mine", response_model=Page[NotificationRead])
async def list_my_notifications(
    is_read: bool | None = Query(default=None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Page[NotificationRead]:
    return await svc.list_my_notifications(
        current_user_id=current_user,
        session=session,
        is_read=is_read,
        page=page,
        size=size,
    )


@router.get("/", response_model=Page[NotificationRead])
async def list_notifications(
    user_id: UUID | None = Query(default=None),
    is_read: bool | None = Query(default=None),
    status: NotificationStatus | None = Query(default=None),
    reference_id: UUID | None = Query(default=None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> Page[NotificationRead]:
    return await svc.list_notifications(
        session=session,
        user_id=user_id,
        is_read=is_read,
        status=status,
        reference_id=reference_id,
        page=page,
        size=size,
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
