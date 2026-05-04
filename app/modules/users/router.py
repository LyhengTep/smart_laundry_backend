from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.db.engine import get_session
from app.lib.security import get_current_user, require_admin
from app.modules.users import service as svc
from app.modules.users.models import UserStatus
from app.modules.users.schema import UserEdit, UserMsgTokenUpdate, UserRead, UserWrite
from app.shared.common import RoleName

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=Page[UserRead])
async def list_users(
    role: RoleName | None = Query(default=None),
    status: UserStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
) -> Page[UserRead]:
    return await svc.list_users(session, role=role, status=status, page=page, size=size)


@router.get("/{user_id}", response_model=UserRead)
async def list_one_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
) -> UserRead:
    return await svc.list_one_user(user_id, session)


@router.post("/", response_model=UserRead)
async def create_users(
    data: UserWrite,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
) -> UserRead:
    return await svc.create_user(data=data, session=session)


@router.post("/admin", response_model=UserRead)
async def create_admin(
    data: UserWrite,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(require_admin),
) -> UserRead:
    return await svc.create_admin(data=data, session=session)


@router.patch("/{user_id}", response_model=UserRead)
async def edit_user(
    user_id: UUID,
    data: UserEdit,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
) -> UserRead:
    return await svc.edit_user(user_id=user_id, data=data, session=session)


@router.patch("/{user_id}/deactivate", response_model=UserRead)
async def deactivate_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
) -> UserRead:
    return await svc.deactivate_user(user_id=user_id, session=session)


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
) -> bool:
    return await svc.delete_user(user_id, session)


@router.patch("/{user_id}/msg-token", response_model=UserRead)
async def update_user_msg_token(
    user_id: UUID,
    data: UserMsgTokenUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
) -> UserRead:
    return await svc.update_user_msg_token(user_id=user_id, data=data, session=session)


@router.patch("/{user_id}/approve", response_model=UserRead)
async def approve_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
) -> UserRead:
    return await svc.approve_user(user_id=user_id, session=session)
