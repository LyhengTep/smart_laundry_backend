from sqlmodel import Field,SQLModel
from sqlalchemy import Column, DateTime, Enum as SAEnum, String, Text
from uuid import UUID, uuid4
from enum import Enum

from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"

class RoleName(str, Enum):
    ADMIN = "ADMIN"
    MERCHANT = "MERCHANT"
    DRIVER = "DRIVER"

class User(SQLModel, table=True):
    __tablename__="users"
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)

    full_name: str = Field(sa_column=Column(String(120), nullable=False))
    user_name: str = Field(sa_column=Column(String(60), nullable=False, unique=True, index=True))
    email: str = Field(sa_column=Column(String(255), nullable=False, unique=True, index=True))
    phone: str | None = Field(default=None, sa_column=Column(String(30), unique=True, nullable=True))

    password_hash: str = Field(sa_column=Column(Text, nullable=False))

    role: str = Field(sa_column=Column(SAEnum(RoleName,name="role_name"),nullable=False))

    status: UserStatus = Field(
        default=UserStatus.ACTIVE,
        sa_column=Column(SAEnum(UserStatus, name="user_status"), nullable=False, index=True),
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )