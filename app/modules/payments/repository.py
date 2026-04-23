import decimal
import uuid
from uuid import UUID

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.lib.datetime import utc_now
from app.modules.payments.models import Payment, PaymentStatus, PaymentType


async def get_by_id(payment_id: UUID, session: AsyncSession) -> Payment | None:
    return await session.get(Payment, payment_id)


async def get_by_order_id(order_id: UUID, session: AsyncSession) -> list[Payment]:
    result = await session.exec(select(Payment).where(Payment.order_id == order_id))
    return list(result.all())


async def get_pending_by_order_id(order_id: UUID, session: AsyncSession) -> Payment | None:
    result = await session.exec(
        select(Payment).where(
            Payment.order_id == order_id,
            Payment.status == PaymentStatus.PENDING,
        )
    )
    return result.one_or_none()


async def get_by_assignment_id(assignment_id: UUID, session: AsyncSession) -> Payment | None:
    result = await session.exec(
        select(Payment).where(Payment.assignment_id == assignment_id)
    )
    return result.one_or_none()


async def get_by_type(
    order_id: UUID,
    payment_type: PaymentType,
    session: AsyncSession,
) -> Payment | None:
    result = await session.exec(
        select(Payment).where(
            Payment.order_id == order_id,
            Payment.type == payment_type,
        )
    )
    return result.one_or_none()


async def list_paginated(
    session: AsyncSession,
    *,
    order_id: UUID | None = None,
    assignment_id: UUID | None = None,
    status: PaymentStatus | None = None,
    payment_type: PaymentType | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[Payment]:
    offset = (page - 1) * size
    statement = select(Payment).order_by(Payment.created_at.desc()).offset(offset).limit(size)
    count_statement = select(func.count(Payment.id))

    if order_id is not None:
        statement = statement.where(Payment.order_id == order_id)
        count_statement = count_statement.where(Payment.order_id == order_id)
    if assignment_id is not None:
        statement = statement.where(Payment.assignment_id == assignment_id)
        count_statement = count_statement.where(Payment.assignment_id == assignment_id)
    if status is not None:
        statement = statement.where(Payment.status == status)
        count_statement = count_statement.where(Payment.status == status)
    if payment_type is not None:
        statement = statement.where(Payment.type == payment_type)
        count_statement = count_statement.where(Payment.type == payment_type)

    total = (await session.exec(count_statement)).one()
    payments = (await session.exec(statement)).all()
    return Page[Payment](items=list(payments), total=total, page=page, size=size, pages=(total + size - 1) // size)


async def save(payment: Payment, session: AsyncSession) -> Payment:
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def delete(payment: Payment, session: AsyncSession) -> None:
    await session.delete(payment)
    await session.commit()
