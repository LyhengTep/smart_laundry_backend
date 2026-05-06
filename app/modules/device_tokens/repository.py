from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.device_tokens.models import DeviceToken


async def get_by_id(token_id: int, session: AsyncSession) -> DeviceToken | None:
    return await session.get(DeviceToken, token_id)


async def get_by_token(token: str, session: AsyncSession) -> DeviceToken | None:
    result = await session.exec(select(DeviceToken).where(DeviceToken.token == token))
    return result.one_or_none()


async def list_by_filters(
    session: AsyncSession,
    *,
    user_id: UUID | None = None,
    driver_id: UUID | None = None,
) -> list[DeviceToken]:
    statement = select(DeviceToken).order_by(DeviceToken.updated_at.desc())
    if user_id is not None:
        statement = statement.where(DeviceToken.user_id == user_id)
    if driver_id is not None:
        statement = statement.where(DeviceToken.driver_id == driver_id)
    result = await session.exec(statement)
    return list(result.all())


async def save(token: DeviceToken, session: AsyncSession) -> DeviceToken:
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


async def delete(token: DeviceToken, session: AsyncSession) -> None:
    await session.delete(token)
    await session.commit()


async def delete_by_user_id(user_id: UUID, session: AsyncSession) -> int:
    result = await session.exec(select(DeviceToken).where(DeviceToken.user_id == user_id))
    tokens = result.all()
    for token in tokens:
        await session.delete(token)
    await session.commit()
    return len(tokens)
