from fastapi import APIRouter
from app import api
from app.modules.users.router import router as users_router
from app.modules.auth.router import router as auth_router

from app.modules.drivers.router import router as driver_router
from app.modules.businesses.router import router as business_router
from app.modules.files.router import router as files_router
from app.modules.laundry_services.router import router as laundry_services_router
from app.modules.business_services.router import router as business_services_router
from app.modules.orders.router import router as orders_router
from app.modules.notifications.router import router as notifications_router
from app.modules.realtime.router import router as realtime_router
from app.modules.device_tokens.router import router as device_tokens_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(driver_router)
api_router.include_router(business_router)
api_router.include_router(auth_router)
api_router.include_router(files_router)
api_router.include_router(laundry_services_router)
api_router.include_router(business_services_router)
api_router.include_router(orders_router)
api_router.include_router(notifications_router)
api_router.include_router(realtime_router)
api_router.include_router(device_tokens_router)
