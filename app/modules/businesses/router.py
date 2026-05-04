from typing import Optional
from urllib import response
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.db.engine import get_session
from app.modules.businesses.models import ShopStatus
from app.modules.businesses.schema import BusinessRead, BusinessUpdate, BusinessWrite, ShopStatusResponse, ShopStatusUpdate, SingleBusinessRead
from app.modules.businesses import service as svc
from app.modules.payments import service as payment_svc
from app.modules.payments.schema import BusinessRevenueRead
from app.shared.passwords import get_current_user


router = APIRouter(prefix="/businesses", tags=["businesses"])

@router.get("/mine", response_model=Page[BusinessRead])
async def list_my_businesses(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Page[BusinessRead]:
    return await svc.list_my_businesses(current_user, session, page, size)


@router.get("/",response_model=Page[BusinessRead])
async def list_businesses(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: Optional[ShopStatus] = Query(None),
    is_open: Optional[bool] = Query(None),
    q: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
) -> Page[BusinessRead]:
    return await svc.list_businesses(session, page, size, status, is_open, q)


@router.get("/{business_id}",response_model=SingleBusinessRead)
async def list_one_business(business_id:UUID,session: AsyncSession = Depends(get_session))->SingleBusinessRead:
    return await svc.list_one_business(business_id,session)

@router.post("/",response_model=BusinessRead)
async def create_business(data:BusinessWrite,current_user: str = Depends(get_current_user),session: AsyncSession = Depends(get_session)):
    return await svc.create_business(data,current_user,session)


@router.put("/{business_id}",response_model=SingleBusinessRead)
async def edit_business(business_id: UUID, data: BusinessUpdate,current_user: str = Depends(get_current_user),session: AsyncSession = Depends(get_session)):
    return await svc.edit_business(business_id,data,current_user,session)

@router.patch("/{business_id}/shop-status", response_model=ShopStatusResponse)
async def toggle_shop_status(
    business_id: UUID,
    data: ShopStatusUpdate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ShopStatusResponse:
    return await svc.toggle_shop_status(business_id, data, current_user, session)


@router.delete("/{business_id}")
async def remove_business(business_id: UUID,current_user: str = Depends(get_current_user),session: AsyncSession = Depends(get_session)):
    return await svc.remove_business(business_id,current_user,session)



@router.get("/{business_id}/revenue", response_model=BusinessRevenueRead)
async def get_business_revenue(
    business_id: UUID,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BusinessRevenueRead:
    return await payment_svc.get_business_revenue(business_id=business_id, session=session)


@router.post("/test")
async def test(current_user: str = Depends(get_current_user)):
    return {"user":current_user}