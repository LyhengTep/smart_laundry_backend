from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship,SQLModel
from sqlalchemy import Column, DateTime, Enum as SAEnum, String, Text, UniqueConstraint
from uuid import UUID, uuid4
from enum import Enum

from datetime import datetime, timezone

# from app.modules.businesses.models import LaundryBusiness

from app.shared.common import RoleName, UserStatus, utc_now
from app.modules.drivers.models import Driver

if TYPE_CHECKING:
    from app.modules.businesses.models import LaundryBusiness
    from app.modules.orders.models import Order




class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("user_name", "role", name="uq_users_user_name_role"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)

    full_name: str = Field(sa_column=Column(String(120), nullable=False))
    user_name: str = Field(sa_column=Column(String(60), nullable=False, index=True))
    email: str = Field(sa_column=Column(String(255), nullable=False))
    phone: str | None = Field(default=None, sa_column=Column(String(30), unique=True, nullable=True))
    msg_token: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    password_hash: str = Field(sa_column=Column(Text, nullable=False))

    role: str = Field(sa_column=Column(SAEnum(RoleName,name="role_name"),nullable=False))

    status: UserStatus = Field(
        default=UserStatus.ACTIVE,
        sa_column=Column(SAEnum(UserStatus, name="user_status"), nullable=False, index=True),
    )

    orders: list["Order"] = Relationship(back_populates="customer")
    driver: Driver | None = Relationship(back_populates="user")
    businesses: list["LaundryBusiness"] = Relationship(back_populates="owner")
    
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
