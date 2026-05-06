from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.exceptions.http import create_400, create_404
from app.modules.device_tokens.models import DeviceToken
from app.modules.device_tokens.schema import DeviceTokenRead, DeviceTokenRegister
from app.modules.device_tokens import repository as repo
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
    return await repo.list_by_filters(session, user_id=user_id, driver_id=driver_id)


async def get_device_token(device_token_id: int, session: AsyncSession) -> DeviceTokenRead:
    token = await repo.get_by_id(device_token_id, session)
    if token is None:
        raise create_404("Device token not found")
    return token


async def register_device_token(data: DeviceTokenRegister, session: AsyncSession) -> DeviceTokenRead:
    _validate_device_token_target(data)
    token = await repo.get_by_token(data.token, session)
    if token is None:
        token = DeviceToken(**data.model_dump())
    else:
        token.user_id = data.user_id
        token.driver_id = data.driver_id
        token.device_type = data.device_type
        token.updated_at = utc_now()
    return await repo.save(token, session)


async def delete_device_token(device_token_id: int, session: AsyncSession) -> bool:
    token = await repo.get_by_id(device_token_id, session)
    if token is None:
        raise create_404("Device token not found")
    await repo.delete(token, session)
    return True


async def delete_device_tokens_by_user_id(user_id: UUID, session: AsyncSession) -> int:
    return await repo.delete_by_user_id(user_id, session)
