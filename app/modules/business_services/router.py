



from fastapi import APIRouter, Depends
from app.db.engine import get_session
from app.modules.business_services import service as svc
from app.modules.business_services.schema import BusinessServiceRead, BusinessServiceWrite

router = APIRouter(prefix="/business-services", tags=["business-services"])


@router.get("/")
async def list_business_services(session=Depends(get_session)) -> list[BusinessServiceRead]:
    result = await svc.list_business_services(session=session)
    return result


@router.post("/")
async def create_business_service(data: BusinessServiceWrite, session=Depends(get_session)) -> BusinessServiceRead: 
    result = await svc.create_business_service(session=session, data=data)
    return result



@router.post("/bulk",response_model=list[BusinessServiceRead])
async def create_business_services(data: list[BusinessServiceWrite], session=Depends(get_session)) -> list[BusinessServiceRead]: 
    result = await svc.create_business_service_bulk(session=session, data=data)
    return result