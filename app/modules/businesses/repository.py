from datetime import datetime
from uuid import UUID

from sqlalchemy import func, and_
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.modules.business_services.model import BusinessService
from app.modules.businesses.models import LaundryBusiness, ShopStatus
from app.modules.orders.models import Order, OrderStatus
from app.modules.reviews.models import ShopReview
from app.modules.reviews.schema import ShopReviewSummary
from app.modules.users.models import User


_ACTIVE_ORDER_STATUSES = [
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
    OrderStatus.PICKUP_ASSIGNED,
    OrderStatus.OUT_FOR_PICKUP,
    OrderStatus.PICKED_UP,
    OrderStatus.DELIVERED_TO_SHOP,
    OrderStatus.PROCESSING,
    OrderStatus.READY_FOR_DELIVERY,
    OrderStatus.DELIVERY_ASSIGNED,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.PICKED_UP_DELIVERY,
]


async def get_by_id(business_id: UUID, session: AsyncSession) -> LaundryBusiness | None:
    result = await session.exec(
        select(LaundryBusiness).where(LaundryBusiness.id == business_id)
    )
    return result.first()


async def get_by_id_with_owner(business_id: UUID, session: AsyncSession) -> LaundryBusiness | None:
    result = await session.exec(
        select(LaundryBusiness)
        .where(LaundryBusiness.id == business_id)
        .options(selectinload(LaundryBusiness.owner))
    )
    return result.first()


async def get_by_id_with_services(business_id: UUID, session: AsyncSession) -> LaundryBusiness | None:
    result = await session.exec(
        select(LaundryBusiness)
        .where(LaundryBusiness.id == business_id)
        .options(
            selectinload(LaundryBusiness.services).selectinload(BusinessService.laundry_service)
        )
    )
    return result.first()


async def batch_review_summaries(
    business_ids: list[UUID], session: AsyncSession
) -> dict[UUID, ShopReviewSummary]:
    if not business_ids:
        return {}
    rows = (
        await session.exec(
            select(
                ShopReview.business_id,
                func.coalesce(func.avg(ShopReview.rating), 0).label("avg_rating"),
                func.count(ShopReview.id).label("total"),
            )
            .where(ShopReview.business_id.in_(business_ids))
            .group_by(ShopReview.business_id)
        )
    ).all()
    return {
        row.business_id: ShopReviewSummary(
            business_id=row.business_id,
            average_rating=round(float(row.avg_rating), 1),
            total_reviews=row.total,
        )
        for row in rows
    }


async def count_active_orders(business_id: UUID, session: AsyncSession) -> int:
    result = await session.exec(
        select(func.count(Order.id)).where(
            Order.business_id == business_id,
            Order.status.in_(_ACTIVE_ORDER_STATUSES),
        )
    )
    return result.one()


async def list_by_owner(
    owner_id: UUID,
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 10,
) -> Page[LaundryBusiness]:
    offset = (page - 1) * size
    statement = (
        select(LaundryBusiness)
        .where(LaundryBusiness.owner_id == owner_id, LaundryBusiness.status != ShopStatus.DEACTIVATED)
        .options(selectinload(LaundryBusiness.owner))
        .offset(offset)
        .limit(size)
    )
    count_statement = select(func.count(LaundryBusiness.id)).where(
        LaundryBusiness.owner_id == owner_id, LaundryBusiness.status != ShopStatus.DEACTIVATED
    )
    total = (await session.exec(count_statement)).one()
    businesses = (await session.exec(statement)).all()
    return Page[LaundryBusiness](
        items=list(businesses),
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


async def list_paginated(
    session: AsyncSession,
    *,
    status: ShopStatus | None = None,
    is_open: bool | None = None,
    q: str | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[LaundryBusiness]:
    offset = (page - 1) * size
    statement = (
        select(LaundryBusiness)
        .join(User)
        .where(LaundryBusiness.status != ShopStatus.DEACTIVATED)
        .options(selectinload(LaundryBusiness.owner))
        .offset(offset)
        .limit(size)
    )
    count_statement = (
        select(func.count(LaundryBusiness.id))
        .join(User)
        .where(LaundryBusiness.status != ShopStatus.DEACTIVATED)
    )

    if status is not None:
        statement = statement.where(LaundryBusiness.status == status)
        count_statement = count_statement.where(LaundryBusiness.status == status)
    if is_open:
        open_statuses = [ShopStatus.APPROVED, ShopStatus.OPEN]
        now = datetime.now().time()
        statement = statement.where(
            and_(
                LaundryBusiness.open_time <= LaundryBusiness.close_time,
                LaundryBusiness.open_time <= now,
                LaundryBusiness.close_time >= now,
            ),
            LaundryBusiness.status.in_(open_statuses),
        )
    if q is not None:
        statement = statement.where(LaundryBusiness.name.ilike(f"%{q}%"))

    total = (await session.exec(count_statement)).one()
    businesses = (await session.exec(statement)).all()
    return Page[LaundryBusiness](
        items=list(businesses),
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


async def get_services_by_business(business_id: UUID, session: AsyncSession) -> list[BusinessService]:
    result = await session.exec(
        select(BusinessService).where(BusinessService.business_id == business_id)
    )
    return list(result.all())


async def get_service_by_id_and_business(
    service_id: UUID, business_id: UUID, session: AsyncSession
) -> BusinessService | None:
    result = await session.exec(
        select(BusinessService).where(
            BusinessService.id == service_id, BusinessService.business_id == business_id
        )
    )
    return result.first()


async def save(business: LaundryBusiness, session: AsyncSession) -> LaundryBusiness:
    session.add(business)
    await session.commit()
    await session.refresh(business)
    return business
