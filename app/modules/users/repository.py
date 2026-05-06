from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.modules.users.models import User, UserStatus
from app.shared.common import RoleName


def _with_driver():
    return selectinload(User.driver)


async def get_by_id(user_id: UUID, session: AsyncSession) -> User | None:
    result = await session.exec(
        select(User).where(User.id == user_id).options(_with_driver())
    )
    return result.one_or_none()


async def get_by_username_and_role(username: str, role: RoleName, session: AsyncSession) -> User | None:
    result = await session.exec(
        select(User).where(User.user_name == username, User.role == role).options(_with_driver())
    )
    return result.one_or_none()


async def get_by_email_and_role(email: str, role: RoleName, session: AsyncSession) -> User | None:
    result = await session.exec(
        select(User).where(User.email == email, User.role == role).options(_with_driver())
    )
    return result.one_or_none()


async def list_paginated(
    session: AsyncSession,
    *,
    role: RoleName | None = None,
    status: UserStatus | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[User]:
    offset = (page - 1) * size
    statement = (
        select(User)
        .options(_with_driver())
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    count_statement = select(func.count(User.id))

    if role is not None:
        statement = statement.where(User.role == role)
        count_statement = count_statement.where(User.role == role)
    if status is not None:
        statement = statement.where(User.status == status)
        count_statement = count_statement.where(User.status == status)

    total = (await session.exec(count_statement)).one()
    users = (await session.exec(statement)).all()
    return Page[User](
        items=list(users),
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


async def save(user: User, session: AsyncSession) -> User:
    session.add(user)
    await session.commit()
    return await get_by_id(user.id, session)


async def delete(user: User, session: AsyncSession) -> None:
    await session.delete(user)
    await session.commit()
