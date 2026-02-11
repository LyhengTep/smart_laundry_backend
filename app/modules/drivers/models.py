from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship,SQLModel
from sqlalchemy import Column, DateTime, Enum as SAEnum, String, Text
from uuid import UUID, uuid4
from enum import Enum

from datetime import datetime, timezone
if TYPE_CHECKING:
    from app.modules.users.models import User

# def utc_now() -> datetime:
#     return datetime.now(timezone.utc)

# class UserStatus(str, Enum):
#     ACTIVE = "ACTIVE"
#     INACTIVE = "INACTIVE"
#     SUSPENDED = "SUSPENDED"

# class RoleName(str, Enum):
#     ADMIN = "ADMIN"
#     MERCHANT = "MERCHANT"
#     DRIVER = "DRIVER"
#     CUSTOMER = "CUSTOMER"

class Driver(SQLModel, table=True):
    __tablename__="drivers"
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    user_id: UUID = Field(foreign_key="users.id")
    plate_number: str = Field(sa_column=Column(String(32), nullable=False))
    id_card_number: str = Field(sa_column=Column(String(64), nullable=False))
    vehicle_type: str = Field(sa_column=Column(String(64), nullable=False))
    user: "User" = Relationship(back_populates="driver")
    # optional extras
    license_number: str = Field(default=None, sa_column=Column(String(64), nullable=True))
    vehicle_color: str = Field(default=None, sa_column=Column(String(32), nullable=True))

