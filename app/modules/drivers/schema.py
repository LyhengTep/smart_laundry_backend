

from datetime import datetime
from uuid import UUID
from sqlmodel import SQLModel

from app.api.reponse_model import Page
from app.modules.drivers.models import DARole, DAStatus, DriverAssignment
from app.modules.orders.schema import OrderRead
from app.modules.users.models import RoleName, UserStatus
from app.modules.users.schema import UserEdit, UserRead, UserWrite
from typing import Optional

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
    user: UserEdit


class DriverAssignmentCreate(SQLModel):
    driver_id: UUID
    order_id: UUID
    role: DARole


class DriverAssignmentRead(SQLModel):
    id: UUID
    driver_id: UUID
    order_id: UUID
    role: DARole | None
    status: DAStatus | None
    assignedAt: datetime | None
    deliveryAt: datetime | None
    order: OrderRead | None
    created_at: datetime
    updated_at: datetime


class DriverAssignmentStatusUpdate(SQLModel):
    status: DAStatus

# class AssignmentRead(DriverAssignment):
    
#     order: Optional[OrderRead] = None

#     model_config = {"from_attributes": True}



# class UserWrite(SQLModel):
#     full_name: str
#     user_name: str
#     password: str
#     email: str
#     phone: str | None
#     role: RoleName
