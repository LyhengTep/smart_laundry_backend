from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.lib.datetime import utc_now
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.users.models import User
from app.modules.businesses.models import LaundryBusiness


async def get_by_id(order_id: UUID, session: AsyncSession) -> Order | None:
    result = await session.exec(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    return result.first()


async def get_by_id_with_relations(order_id: UUID, session: AsyncSession) -> Order | None:
    result = await session.exec(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items),
            selectinload(Order.customer),
            selectinload(Order.business),
            selectinload(Order.payments),
        )
    )
    return result.first()


async def get_by_order_no(order_no: str, session: AsyncSession) -> Order | None:
    result = await session.exec(
        select(Order)
        .where(Order.order_no == order_no)
        .options(selectinload(Order.items))
    )
    return result.first()


async def list_paginated(
    session: AsyncSession,
    *,
    customer_id: UUID | None = None,
    business_id: UUID | None = None,
    driver_id: UUID | None = None,
    order_no: str | None = None,
    status: OrderStatus | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[Order]:
    offset = (page - 1) * size
    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    count_statement = select(func.count(Order.id))

    if customer_id is not None:
        statement = statement.where(Order.customer_id == customer_id)
        count_statement = count_statement.where(Order.customer_id == customer_id)
    if business_id is not None:
        statement = statement.where(Order.business_id == business_id)
        count_statement = count_statement.where(Order.business_id == business_id)
    if driver_id is not None:
        statement = statement.where(Order.driver_id == driver_id)
        count_statement = count_statement.where(Order.driver_id == driver_id)
    if order_no is not None:
        statement = statement.where(Order.order_no.ilike(f"%{order_no}%"))
        count_statement = count_statement.where(Order.order_no.ilike(f"%{order_no}%"))
    if status is not None:
        statement = statement.where(Order.status == status)
        count_statement = count_statement.where(Order.status == status)

    total = (await session.exec(count_statement)).one()
    orders = (await session.exec(statement)).all()
    return Page[Order](items=list(orders), total=total, page=page, size=size, pages=(total + size - 1) // size)


async def list_by_statuses(
    session: AsyncSession,
    statuses: list[OrderStatus],
    business_id: UUID | None = None,
) -> list[Order]:
    statement = (
        select(Order)
        .where(Order.status.in_(statuses))
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    if business_id is not None:
        statement = statement.where(Order.business_id == business_id)
    result = await session.exec(statement)
    return list(result.all())


async def save(order: Order, session: AsyncSession) -> Order:
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def save_item(item: OrderItem, session: AsyncSession) -> OrderItem:
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def get_item_by_id(item_id: UUID, session: AsyncSession) -> OrderItem | None:
    return await session.get(OrderItem, item_id)
