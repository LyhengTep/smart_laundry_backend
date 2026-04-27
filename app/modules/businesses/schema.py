

from datetime import datetime, time
from enum import Enum
from uuid import UUID
from rich import status
from sqlmodel import SQLModel

from app.modules.business_services.schema import BusinessServiceRead, BusinessServiceUpdate
from app.modules.reviews.schema import ShopReviewSummary


class BusinessRead(SQLModel):
    id: UUID
    owner_id: UUID
    name: str
    address: str
    phone: str | None
    latitude: float | None
    longitude: float | None
    profile_image_url: str | None
    cover_image_url: str | None
    rating_avg: float
    business_license_number: str | None
    status: str
    open_time: time
    close_time: time
    created_at: datetime
    updated_at: datetime
    review_summary: ShopReviewSummary | None = None
    model_config = {"from_attributes": True}


class BusinessWrite(SQLModel):
    name: str
    address: str
    phone: str | None
    latitude: float | None
    longitude: float | None
    profile_image_url: str | None
    cover_image_url: str | None
    open_time: time
    close_time: time



class BusinessUpdate(BusinessWrite):
    services: list[BusinessServiceUpdate] | None



class SingleBusinessRead(BusinessRead):
    services: list[BusinessServiceRead]


class ShopStatusAction(str, Enum):
    CLOSE = "CLOSE"
    OPEN = "OPEN"


class ShopStatusUpdate(SQLModel):
    action: ShopStatusAction
    force: bool = False


class ShopStatusResponse(SQLModel):
    shop_id: UUID
    status: str
    message: str
    warning: str | None = None
    active_order_count: int | None = None
