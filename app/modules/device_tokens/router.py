from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.engine import get_session
from app.modules.device_tokens import service as svc
from app.modules.device_tokens.schema import DeviceTokenRead, DeviceTokenRegister


router = APIRouter(prefix="/device-tokens", tags=["device-tokens"])


@router.get("/", response_model=list[DeviceTokenRead])
async def list_device_tokens(
    user_id: UUID | None = Query(default=None),
    driver_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[DeviceTokenRead]:
    return await svc.list_device_tokens(session=session, user_id=user_id, driver_id=driver_id)


@router.get("/{device_token_id}", response_model=DeviceTokenRead)
async def get_device_token(
    device_token_id: int,
    session: AsyncSession = Depends(get_session),
) -> DeviceTokenRead:
    return await svc.get_device_token(device_token_id=device_token_id, session=session)


@router.post("/register", response_model=DeviceTokenRead)
async def register_device_token(
    data: DeviceTokenRegister,
    session: AsyncSession = Depends(get_session),
) -> DeviceTokenRead:
    return await svc.register_device_token(data=data, session=session)


@router.delete("/{device_token_id}", response_model=bool)
async def delete_device_token(
    device_token_id: int,
    session: AsyncSession = Depends(get_session),
) -> bool:
    return await svc.delete_device_token(device_token_id=device_token_id, session=session)
