


from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel

from app.modules.business_services.model import PriceType
from app.modules.laundry_services.schema import LaundryServiceRead


class BusinessServiceRead(SQLModel):
    id: UUID
    business_id: UUID
    service_id: int
    base_price: float
    is_active: bool
    created_at: datetime 
    updated_at: datetime
    laundry_service: LaundryServiceRead
    pricing_type: PriceType
    # business: BusinessRead



class BusinessServiceWrite(SQLModel):
    business_id: UUID
    service_id: int
    base_price: float
    pricing_type: PriceType



class BusinessServiceUpdate(BusinessServiceWrite):
    id: UUID| None = None

