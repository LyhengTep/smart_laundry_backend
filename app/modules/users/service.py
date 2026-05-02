from __future__ import annotations
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.api.reponse_model import Page
from app.exceptions.http import create_400, create_404
from app.modules.users.models import User, UserStatus
from app.modules.users.schema import UserEdit, UserMsgTokenUpdate, UserRead, UserWrite
from app.shared.common import RoleName
from app.shared.passwords import hash_password
import logging


logger = logging.getLogger(__name__)


async def _fetch_user(user_id: UUID, session: AsyncSession) -> User | None:
    result = await session.exec(select(User).where(User.id == user_id).options(selectinload(User.driver)))
    return result.one_or_none()


async def list_users(
    session: AsyncSession,
    *,
    role: RoleName | None = None,
    status: UserStatus | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[UserRead]:
    """Return a paginated list of users, optionally filtered by role and/or status."""
    offset = (page - 1) * size
    statement = select(User).options(selectinload(User.driver)).order_by(User.created_at.desc()).offset(offset).limit(size)
    count_statement = select(func.count(User.id))

    if role is not None:
        statement = statement.where(User.role == role)
        count_statement = count_statement.where(User.role == role)
    if status is not None:
        statement = statement.where(User.status == status)
        count_statement = count_statement.where(User.status == status)

    total = (await session.exec(count_statement)).one()
    users = (await session.exec(statement)).all()
    return Page[UserRead](
        items=users,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


async def approve_user(user_id: UUID, session: AsyncSession) -> UserRead:
    """Set user status to ACTIVE; raises 404 if not found, 400 if already active."""
    user = await _fetch_user(user_id, session)
    if user is None:
        raise create_404("User not found")
    if user.status == UserStatus.ACTIVE:
        raise create_400("User is already active")
    user.status = UserStatus.ACTIVE
    session.add(user)
    await session.commit()
    return await _fetch_user(user_id, session)


async def list_one_user(user_id: UUID, session: AsyncSession) -> UserRead:
    user = await _fetch_user(user_id, session)
    if user is None:
        raise create_404("User not found")
    return user


async def create_user(data: UserWrite, session: AsyncSession) -> UserRead:
    try:
        logging.info("Calling create user %s", data.model_dump())
        user = User(**data.model_dump(exclude={"password"}))
        user.password_hash = hash_password(data.password)
        session.add(user)
        await session.commit()
        return await _fetch_user(user.id, session)
    except Exception as e:
        logging.exception("Failed to create user and need to rollback")
        await session.rollback()
        raise e
    

async def edit_user(user_id: UUID, data: UserEdit, session: AsyncSession) -> UserRead:
    """Update user fields; raises 404 if not found."""
    user = await _fetch_user(user_id, session)
    if user is None:
        raise create_404("User not found")
    for key, value in data.model_dump(exclude_unset=True, exclude={"password"}).items():
        setattr(user, key, value)
    if data.password:
        user.password_hash = hash_password(data.password)
    session.add(user)
    await session.commit()
    return await _fetch_user(user_id, session)


async def deactivate_user(user_id: UUID, session: AsyncSession) -> UserRead:
    """Set user status to INACTIVE; raises 404 if not found, 400 if already inactive."""
    user = await _fetch_user(user_id, session)
    if user is None:
        raise create_404("User not found")
    if user.status == UserStatus.INACTIVE:
        raise create_400("User is already inactive")
    user.status = UserStatus.INACTIVE
    session.add(user)
    await session.commit()
    return await _fetch_user(user_id, session)


async def delete_user(user_id: UUID, session: AsyncSession) -> bool:
    """Permanently delete a user; raises 404 if not found."""
    user = await _fetch_user(user_id, session)
    if user is None:
        raise create_404("User not found")
    await session.delete(user)
    await session.commit()
    return True


async def update_user_msg_token(
    user_id: UUID,
    data: UserMsgTokenUpdate,
    session: AsyncSession,
) -> UserRead:
    logger.info(f"---------------------call add token {user_id}---------------------")
    statement = select(User).where(User.id==user_id).options(selectinload(User.driver))
    user_res = await session.exec(statement)
    user= user_res.one_or_none()
    if user is None:
        raise create_404("User not found")
    logger.info(f"user token is {data.msg_token}")
    user.msg_token = data.msg_token
    session.add(user)
    await session.commit()
    return await _fetch_user(user_id, session)
