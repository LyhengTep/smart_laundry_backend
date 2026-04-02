from uuid import UUID

from sqlmodel import SQLModel

from app.shared.common import RoleName


class UserReadBasicRead(SQLModel):
    id: UUID
    full_name: str
    user_name: str
    email: str
    phone: str | None
    role: RoleName

class DriverBasicRead(SQLModel):
    id: UUID
    user_id: UUID
    plate_number: str
    id_card_number: str
    vehicle_type: str
    license_number: str | None
    vehicle_color: str