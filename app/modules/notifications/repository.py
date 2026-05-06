from uuid import UUID

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.modules.notifications.models import Notification, NotificationStatus


async def get_by_id(notification_id: UUID, session: AsyncSession) -> Notification | None:
    return await session.get(Notification, notification_id)


async def list_paginated(
    session: AsyncSession,
    *,
    user_id: UUID | None = None,
    is_read: bool | None = None,
    status: NotificationStatus | None = None,
    reference_id: UUID | None = None,
    page: int = 1,
    size: int = 20,
) -> Page[Notification]:
    offset = (page - 1) * size
    statement = select(Notification).order_by(Notification.created_at.desc()).offset(offset).limit(size)
    count_statement = select(func.count(Notification.id))

    if user_id is not None:
        statement = statement.where(Notification.user_id == user_id)
        count_statement = count_statement.where(Notification.user_id == user_id)
    if is_read is not None:
        statement = statement.where(Notification.is_read == is_read)
        count_statement = count_statement.where(Notification.is_read == is_read)
    if status is not None:
        statement = statement.where(Notification.status == status)
        count_statement = count_statement.where(Notification.status == status)
    if reference_id is not None:
        statement = statement.where(Notification.reference_id == reference_id)
        count_statement = count_statement.where(Notification.reference_id == reference_id)

    total = (await session.exec(count_statement)).one()
    items = (await session.exec(statement)).all()
    return Page[Notification](
        items=list(items),
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


async def save(notification: Notification, session: AsyncSession) -> Notification:
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification
