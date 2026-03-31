from os import close
import uuid
from datetime import datetime, time
from enum import Enum
from typing import TYPE_CHECKING,  Optional

from sqlalchemy import Column, DateTime, String
from sqlmodel import SQLModel, Field, Relationship

from app.shared.common import utc_now




if TYPE_CHECKING:
    from app.modules.business_services.model import BusinessService
    from app.modules.users.models import User



# ================= ENUM =================
class ShopStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SUSPENDED = "SUSPENDED"
    PENDING_DEACTIVATION = "PENDING_DEACTIVATION"
    DEACTIVATED = "DEACTIVATED"



# ================= LAUNDRY BUSINESS MODEL =================
class LaundryBusiness(SQLModel, table=True):
    __tablename__ = "laundry_businesses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    owner_id: uuid.UUID = Field(foreign_key="users.id")

    name: str
    address: str
    phone: Optional[str] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    profile_image_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    business_license_number: str = Field(sa_column=Column(String(255), nullable=False))
    services: list["BusinessService"] = Relationship(back_populates="business")
    rating_avg: float = 0.0
    open_time: time
    close_time: time
    status: ShopStatus = Field(default=ShopStatus.PENDING)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relationship
    owner: "User" = Relationship(back_populates="businesses")
