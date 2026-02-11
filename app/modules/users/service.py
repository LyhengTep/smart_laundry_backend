from __future__ import annotations
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.modules.users.models import User
from app.modules.users.schema import UserRead, UserWrite
from app.shared.passwords import hash_password
import logging

async def list_users(session: AsyncSession) -> list[UserRead]:
    result = await session.exec(select(User))
    return result.all()


async def create_user(data:UserWrite,session: AsyncSession,) -> UserRead:
    try:
        logging.info("Calling create user %s",data.model_dump())
        user= User(**data.model_dump(exclude={"password"}))
        user.password_hash=hash_password(data.password)
        print(user.password_hash)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        print(user)
        return user
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