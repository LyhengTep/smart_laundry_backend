from __future__ import annotations
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from app.api.reponse_model import Page
from app.exceptions.http import create_400, create_404
from app.modules.users.models import User, UserStatus
from app.modules.users.schema import UserEdit, UserMsgTokenUpdate, UserRead, UserWrite
from app.modules.users import repository as repo
from app.shared.common import RoleName
from app.shared.passwords import hash_password
import logging


logger = logging.getLogger(__name__)


async def list_users(
    session: AsyncSession,
    *,
    role: RoleName | None = None,
    status: UserStatus | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[UserRead]:
    """Return a paginated list of users, optionally filtered by role and/or status."""
    return await repo.list_paginated(session, role=role, status=status, page=page, size=size)


async def approve_user(user_id: UUID, session: AsyncSession) -> UserRead:
    """Set user status to ACTIVE; raises 404 if not found, 400 if already active."""
    user = await repo.get_by_id(user_id, session)
    if user is None:
        raise create_404("User not found")
    if user.status == UserStatus.ACTIVE:
        raise create_400("User is already active")
    user.status = UserStatus.ACTIVE
    return await repo.save(user, session)


async def list_one_user(user_id: UUID, session: AsyncSession) -> UserRead:
    user = await repo.get_by_id(user_id, session)
    if user is None:
        raise create_404("User not found")
    return user


async def create_user(data: UserWrite, session: AsyncSession) -> UserRead:
    try:
        logging.info("Calling create user %s", data.model_dump())
        user = User(**data.model_dump(exclude={"password"}))
        user.password_hash = hash_password(data.password)
        return await repo.save(user, session)
    except Exception as e:
        logging.exception("Failed to create user and need to rollback")
        await session.rollback()
        raise e


async def create_admin(data: UserWrite, session: AsyncSession) -> UserRead:
    """Create a new admin user; forces role=ADMIN and status=ACTIVE regardless of input."""
    try:
        user = User(**data.model_dump(exclude={"password", "role"}))
        user.role = RoleName.ADMIN
        user.status = UserStatus.ACTIVE
        user.password_hash = hash_password(data.password)
        return await repo.save(user, session)
    except Exception as e:
        await session.rollback()
        raise e


async def edit_user(user_id: UUID, data: UserEdit, session: AsyncSession) -> UserRead:
    """Update user fields; raises 404 if not found."""
    user = await repo.get_by_id(user_id, session)
    if user is None:
        raise create_404("User not found")
    for key, value in data.model_dump(exclude_unset=True, exclude={"password"}).items():
        setattr(user, key, value)
    if data.password:
        user.password_hash = hash_password(data.password)
    return await repo.save(user, session)


async def deactivate_user(user_id: UUID, session: AsyncSession) -> UserRead:
    """Set user status to INACTIVE; raises 404 if not found, 400 if already inactive."""
    user = await repo.get_by_id(user_id, session)
    if user is None:
        raise create_404("User not found")
    if user.status == UserStatus.INACTIVE:
        raise create_400("User is already inactive")
    user.status = UserStatus.INACTIVE
    return await repo.save(user, session)


async def delete_user(user_id: UUID, session: AsyncSession) -> bool:
    """Permanently delete a user; raises 404 if not found."""
    user = await repo.get_by_id(user_id, session)
    if user is None:
        raise create_404("User not found")
    await repo.delete(user, session)
    return True


async def update_user_msg_token(
    user_id: UUID,
    data: UserMsgTokenUpdate,
    session: AsyncSession,
) -> UserRead:
    logger.info(f"---------------------call add token {user_id}---------------------")
    user = await repo.get_by_id(user_id, session)
    if user is None:
        raise create_404("User not found")
    logger.info(f"user token is {data.msg_token}")
    user.msg_token = data.msg_token
    return await repo.save(user, session)
