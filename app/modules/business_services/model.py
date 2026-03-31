
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, Integer, String, Text
from sqlmodel import SQLModel
from sqlmodel import Field, Relationship,SQLModel

from app.shared.common import utc_now

if TYPE_CHECKING:
    from app.modules.businesses.models import LaundryBusiness
    from app.modules.laundry_services.model import LaundryService



class PriceType(str, Enum):
    PER_ITEM = "per_item"
    PER_WEIGHT = "per_kg"
    FIXED = "fixed"


class BusinessService(SQLModel, table=True):
    __tablename__="business_services"
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    business_id: UUID = Field(foreign_key="laundry_businesses.id", nullable=False)
    service_id: int = Field(foreign_key="laundry_services.id", nullable=False)
    base_price: float=Field(sa_column=Column(Float(), nullable=False))
    is_active: bool = Field(default=True)
    pricing_type: PriceType = Field(sa_column=Column(SAEnum(PriceType), nullable=False))
    laundry_service: "LaundryService" = Relationship(back_populates="business_service")
    business: "LaundryBusiness" = Relationship(back_populates="services")
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
