

from datetime import datetime
import email
from uuid import UUID
from sqlmodel import SQLModel

from app.modules.users.models import RoleName, UserStatus
from app.modules.users.schema import UserRead, UserWrite


class DriverRead(SQLModel):
    id: UUID
    user_id: UUID
    plate_number: str
    id_card_number: str
    vehicle_type: str
    license_number: str | None
    vehicle_color: str
    user: UserRead


class DriverWrite(SQLModel):
    plate_number: str
    id_card_number: str
    vehicle_type: str
    license_number: str | None
    vehicle_color: str
    user: UserWrite

# class UserWrite(SQLModel):
#     full_name: str
#     user_name: str
#     password: str
#     email: str
#     phone: str | None
#     role: RoleName