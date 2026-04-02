from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlmodel import Field, SQLModel

from app.shared.common import utc_now


class DeviceToken(SQLModel, table=True):
    __tablename__ = "device_tokens"

    id: int | None = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    user_id: UUID | None = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    driver_id: UUID | None = Field(default=None, foreign_key="drivers.id", nullable=True, index=True)
    token: str = Field(sa_column=Column(Text, nullable=False, unique=True, index=True))
    device_type: str = Field(sa_column=Column(String(50), nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
