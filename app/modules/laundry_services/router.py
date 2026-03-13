from uuid import UUID
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.engine import get_session
from app.modules.businesses.models import LaundryBusiness
from app.modules.laundry_services.schema import LaundryServiceRead, LaundryServiceWrite
from app.modules.laundry_services import service as svc


router = APIRouter(prefix="/laundry-services", tags=["laundry-services"])

@router.get("/")
async def list_laundry_services(session: AsyncSession = Depends(get_session))->list[LaundryServiceRead]:
    return await svc.list_laundry_services(session)



@router.post("/")
async def create_laundry_service(data: LaundryServiceWrite, session: AsyncSession = Depends(get_session)) -> LaundryServiceRead:
    return await svc.create_laundry_service(data, session)  
