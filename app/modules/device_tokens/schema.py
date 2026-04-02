from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel


class DeviceTokenRegister(SQLModel):
    user_id: UUID | None = None
    driver_id: UUID | None = None
    token: str
    device_type: str


class DeviceTokenRead(SQLModel):
    id: int
    user_id: UUID | None
    driver_id: UUID | None
    token: str
    device_type: str
    created_at: datetime
    updated_at: datetime
