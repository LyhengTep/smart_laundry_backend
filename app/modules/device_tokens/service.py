from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.exceptions.http import create_400, create_404
from app.modules.device_tokens.models import DeviceToken
from app.modules.device_tokens.schema import DeviceTokenRead, DeviceTokenRegister
from app.shared.common import utc_now


def _validate_device_token_target(data: DeviceTokenRegister) -> None:
    if data.user_id is None and data.driver_id is None:
        raise create_400("Either user_id or driver_id is required")


async def list_device_tokens(
    session: AsyncSession,
    *,
    user_id: UUID | None = None,
    driver_id: UUID | None = None,
) -> list[DeviceTokenRead]:
    statement = select(DeviceToken).order_by(DeviceToken.updated_at.desc())
    if user_id is not None:
        statement = statement.where(DeviceToken.user_id == user_id)
    if driver_id is not None:
        statement = statement.where(DeviceToken.driver_id == driver_id)

    result = await session.exec(statement)
    return result.all()


async def get_device_token(device_token_id: int, session: AsyncSession) -> DeviceTokenRead:
    device_token = await session.get(DeviceToken, device_token_id)
    if device_token is None:
        raise create_404("Device token not found")
    return device_token


async def register_device_token(data: DeviceTokenRegister, session: AsyncSession) -> DeviceTokenRead:
    _validate_device_token_target(data)

    statement = select(DeviceToken).where(DeviceToken.token == data.token)
    result = await session.exec(statement)
    device_token = result.one_or_none()

    if device_token is None:
        device_token = DeviceToken(**data.model_dump())
    else:
        device_token.user_id = data.user_id
        device_token.driver_id = data.driver_id
        device_token.device_type = data.device_type
        device_token.updated_at = utc_now()

    session.add(device_token)
    await session.commit()
    await session.refresh(device_token)
    return device_token


async def delete_device_token(device_token_id: int, session: AsyncSession) -> bool:
    device_token = await session.get(DeviceToken, device_token_id)
    if device_token is None:
        raise create_404("Device token not found")

    await session.delete(device_token)
    await session.commit()
    return True
