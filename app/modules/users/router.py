from uuid import UUID
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.engine import get_session
from app.modules.users import service as svc
from app.modules.users.schema import UserRead, UserWrite

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
async def list_users(session: AsyncSession = Depends(get_session))->list[UserRead]:
    return await svc.list_users(session)

@router.post("/")
async def create_users(data:UserWrite,session: AsyncSession = Depends(get_session))-> UserRead:
    return await svc.create_user(data=data,session=session)


@router.delete("/{user_id}")
async def delete_user(user_id: UUID,session: AsyncSession = Depends(get_session))->bool: 
    return await svc.delete_user(user_id,session)