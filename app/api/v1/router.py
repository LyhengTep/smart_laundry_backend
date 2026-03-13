from fastapi import APIRouter
from app import api
from app.modules.users.router import router as users_router
from app.modules.auth.router import router as auth_router

from app.modules.drivers.router import router as driver_router
from app.modules.businesses.router import router as business_router
from app.modules.files.router import router as files_router
from app.modules.laundry_services.router import router as laundry_services_router
from app.modules.business_services.router import router as business_services_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(driver_router)
api_router.include_router(business_router)
api_router.include_router(auth_router)
api_router.include_router(files_router)
api_router.include_router(laundry_services_router)
api_router.include_router(business_services_router)