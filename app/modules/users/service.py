from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.exceptions.http import create_404
from app.modules.users.models import User
from app.modules.users.schema import UserMsgTokenUpdate, UserRead, UserWrite
from app.shared.passwords import hash_password
import logging



logger=logging.getLogger(__name__)
async def _fetch_user(user_id: UUID, session: AsyncSession) -> User | None:
    result = await session.exec(select(User).where(User.id == user_id).options(selectinload(User.driver)))
    return result.one_or_none()


async def list_users(session: AsyncSession) -> list[UserRead]:
    result = await session.exec(select(User).options(selectinload(User.driver)))
    return result.all()


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
    

async def delete_user(user_id:str, session: AsyncSession) -> bool:
    try:
        clause = await session.exec(select(User).where(User.id==user_id))
        user= clause.one_or_none()
        if user is None:
            return False
        await session.delete(user)
        await session.commit()
        return True
    except Exception as e:    
        return False


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
