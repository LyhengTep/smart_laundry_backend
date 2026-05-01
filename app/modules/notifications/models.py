from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, String, Text
from sqlmodel import Field, SQLModel

from app.shared.common import utc_now


class NotificationType(str, Enum):
    ORDER_STATUS = "ORDER_STATUS"
    PAYMENT = "PAYMENT"
    SYSTEM = "SYSTEM"


class NotificationChannel(str, Enum):
    IN_APP = "IN_APP"
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    SMS = "SMS"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    READ = "READ"


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    type: NotificationType = Field(
        sa_column=Column(SAEnum(NotificationType, name="notification_type"), nullable=False, index=True),
    )
    title: str = Field(sa_column=Column(String(255), nullable=False))
    message: str = Field(sa_column=Column(Text, nullable=False))
    reference_id: UUID | None = Field(default=None, nullable=True, index=True)
    reference_type: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    is_read: bool = Field(default=False, sa_column=Column(Boolean(), nullable=False, index=True))
    channel: NotificationChannel = Field(
        sa_column=Column(SAEnum(NotificationChannel, name="notification_channel"), nullable=False),
    )
    status: NotificationStatus = Field(
        default=NotificationStatus.PENDING,
        sa_column=Column(SAEnum(NotificationStatus, name="notification_status"), nullable=False, index=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    read_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
