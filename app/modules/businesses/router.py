from typing import Optional
from urllib import response
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.db.engine import get_session
from app.modules.businesses.schema import BusinessRead, BusinessUpdate, BusinessWrite, SingleBusinessRead
from app.modules.businesses import service as svc
from app.modules.users.models import UserStatus
from app.shared.passwords import get_current_user


router = APIRouter(prefix="/businesses", tags=["businesses"])

@router.get("/",response_model=Page[BusinessRead])
async def list_businesses(page: int =Query(1,ge=1),size: int=Query(10,ge=1,le=100),
                       status: Optional[UserStatus]=Query(None),
                       session: AsyncSession = Depends(get_session))->list[BusinessRead]:

    return await svc.list_businesses(session,page,size,status)


@router.get("/{business_id}",response_model=SingleBusinessRead)
async def list_one_business(business_id:UUID,session: AsyncSession = Depends(get_session))->SingleBusinessRead:
    return await svc.list_one_business(business_id,session)

@router.post("/",response_model=BusinessRead)
async def create_business(data:BusinessWrite,current_user: str = Depends(get_current_user),session: AsyncSession = Depends(get_session)):
    return await svc.create_business(data,current_user,session)


@router.put("/{business_id}",response_model=SingleBusinessRead)
async def edit_business(business_id: UUID, data: BusinessUpdate,current_user: str = Depends(get_current_user),session: AsyncSession = Depends(get_session)):
    return await svc.edit_business(business_id,data,current_user,session)

@router.delete("/{business_id}")
async def remove_business(business_id: UUID,current_user: str = Depends(get_current_user),session: AsyncSession = Depends(get_session)):
    return await svc.remove_business(business_id,current_user,session)



@router.post("/test")
async def test(current_user: str = Depends(get_current_user)):
    return {"user":current_user}