
from enum import Enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Relationship, SQLModel,Field
from sqlalchemy import Column, DateTime, Enum as SAEnum, String, Text

from app.shared.common import utc_now
if TYPE_CHECKING:
    from app.modules.business_services.model import BusinessService

# ================= ENUM =================
class ServiceEnum(str, Enum):
    WASH = "WASH"
    DRY_CLEAN = "DRY_CLEAN"
    IRON = "IRON"
   

class LaundryService(SQLModel, table=True):
    __tablename__="laundry_services"
    id: int = Field(default=None, primary_key=True)
    name: ServiceEnum = Field(sa_column=Column(SAEnum(ServiceEnum, name="service_enum"), nullable=False, unique=True))
    code: str = Field(sa_column=Column(String(50), nullable=False, unique=True))
    description: str = Field(sa_column=Column(String(100), nullable=False, unique=True))
    business_service: "BusinessService" = Relationship(back_populates="laundry_service")
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
