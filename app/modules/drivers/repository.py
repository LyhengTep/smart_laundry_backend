from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.modules.drivers.models import (
    DARole,
    DAStatus,
    Driver,
    DriverAssignment,
    DriverAssignmentHistory,
    DriverStatus,
)
from app.modules.orders.models import Order
from app.modules.users.models import User, UserStatus


def _driver_with_user_options():
    return selectinload(Driver.user).selectinload(User.driver)


def _assignment_with_full_relations():
    return [
        selectinload(DriverAssignment.order).selectinload(Order.items),
        selectinload(DriverAssignment.order).selectinload(Order.business),
        selectinload(DriverAssignment.order).selectinload(Order.customer).selectinload(User.driver),
        selectinload(DriverAssignment.payment),
    ]


# ---------------------------------------------------------------------------
# Driver queries
# ---------------------------------------------------------------------------

async def get_by_id(driver_id: UUID, session: AsyncSession) -> Driver | None:
    result = await session.exec(
        select(Driver).where(Driver.id == driver_id).options(_driver_with_user_options())
    )
    return result.one_or_none()


async def get_by_user_id(user_id: UUID, session: AsyncSession) -> Driver | None:
    result = await session.exec(
        select(Driver).where(Driver.user_id == user_id).options(_driver_with_user_options())
    )
    return result.one_or_none()


async def list_paginated(
    session: AsyncSession,
    *,
    status: UserStatus | None = None,
    user_name: str | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[Driver]:
    offset = (page - 1) * size
    statement = (
        select(Driver)
        .join(User)
        .options(_driver_with_user_options())
        .offset(offset)
        .limit(size)
    )
    count_statement = select(func.count(Driver.id)).join(User)

    if status is not None:
        statement = statement.where(User.status == status)
        count_statement = count_statement.where(User.status == status)
    if user_name is not None:
        statement = statement.where(User.user_name.ilike(f"%{user_name}%"))
        count_statement = count_statement.where(User.user_name.ilike(f"%{user_name}%"))

    total = (await session.exec(count_statement)).one()
    drivers = (await session.exec(statement)).all()
    return Page[Driver](
        items=list(drivers),
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


async def save_driver(driver: Driver, session: AsyncSession) -> Driver:
    session.add(driver)
    await session.commit()
    return await get_by_id(driver.id, session)


# ---------------------------------------------------------------------------
# Assignment queries
# ---------------------------------------------------------------------------

async def get_assignment_by_id(assignment_id: UUID, session: AsyncSession) -> DriverAssignment | None:
    result = await session.exec(
        select(DriverAssignment).where(DriverAssignment.id == assignment_id)
    )
    return result.one_or_none()


async def get_assignment_with_items(assignment_id: UUID, session: AsyncSession) -> DriverAssignment | None:
    result = await session.exec(
        select(DriverAssignment)
        .where(DriverAssignment.id == assignment_id)
        .options(selectinload(DriverAssignment.order).selectinload(Order.items))
    )
    return result.first()


async def get_assignment_with_full_relations(assignment_id: UUID, session: AsyncSession) -> DriverAssignment | None:
    result = await session.exec(
        select(DriverAssignment)
        .where(DriverAssignment.id == assignment_id)
        .options(*_assignment_with_full_relations())
    )
    return result.first()


async def get_assignment_by_order_and_role(
    order_id: UUID, role: DARole, session: AsyncSession
) -> DriverAssignment | None:
    result = await session.exec(
        select(DriverAssignment).where(
            DriverAssignment.order_id == order_id,
            DriverAssignment.role == role,
        )
    )
    return result.one_or_none()


async def get_pending_assignment_by_driver(driver_id: UUID, session: AsyncSession) -> DriverAssignment | None:
    result = await session.exec(
        select(DriverAssignment)
        .where(DriverAssignment.driver_id == driver_id, DriverAssignment.status == None)
        .options(*_assignment_with_full_relations())
    )
    return result.one_or_none()


async def get_active_assignment_by_driver(driver_id: UUID, session: AsyncSession) -> DriverAssignment | None:
    result = await session.exec(
        select(DriverAssignment)
        .where(
            DriverAssignment.driver_id == driver_id,
            DriverAssignment.status == DAStatus.ACCEPTED,
        )
        .options(selectinload(DriverAssignment.order).selectinload(Order.items))
    )
    return result.one_or_none()


async def list_assignments_paginated(
    session: AsyncSession,
    *,
    driver_id: UUID | None = None,
    order_id: UUID | None = None,
    role: DARole | None = None,
    status: DAStatus | None = None,
    status_not_in: list[DAStatus] | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[DriverAssignment]:
    offset = (page - 1) * size
    statement = (
        select(DriverAssignment)
        .options(*_assignment_with_full_relations())
        .order_by(DriverAssignment.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    count_statement = select(func.count(DriverAssignment.id))

    if status_not_in:
        statement = statement.where(DriverAssignment.status.notin_(status_not_in))
        count_statement = count_statement.where(DriverAssignment.status.notin_(status_not_in))
    if driver_id is not None:
        statement = statement.where(DriverAssignment.driver_id == driver_id)
        count_statement = count_statement.where(DriverAssignment.driver_id == driver_id)
    if order_id is not None:
        statement = statement.where(DriverAssignment.order_id == order_id)
        count_statement = count_statement.where(DriverAssignment.order_id == order_id)
    if role is not None:
        statement = statement.where(DriverAssignment.role == role)
        count_statement = count_statement.where(DriverAssignment.role == role)
    if status is not None:
        statement = statement.where(DriverAssignment.status == status)
        count_statement = count_statement.where(DriverAssignment.status == status)

    total = (await session.exec(count_statement)).one()
    assignments = (await session.exec(statement)).all()
    return Page[DriverAssignment](
        items=list(assignments),
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


async def save_assignment(assignment: DriverAssignment, session: AsyncSession) -> DriverAssignment:
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def save_assignment_history(history: DriverAssignmentHistory, session: AsyncSession) -> DriverAssignmentHistory:
    session.add(history)
    await session.commit()
    return history
