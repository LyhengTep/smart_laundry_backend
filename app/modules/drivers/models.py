
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship,SQLModel
from sqlalchemy import Column, DateTime, Enum as SAEnum, String, Text
from uuid import UUID, uuid4
from enum import Enum
from app.modules.orders.models import Order
from app.shared.common import utc_now
from datetime import datetime, timezone
if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.payments.models import Payment

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
class DriverStatus(str, Enum):
    OFFLINE = "OFFLINE"              # Not using the app / logged out
    ONLINE = "ONLINE"                # Available to receive orders
    BUSY = "BUSY"                    # Assigned to an order
    PICKING_UP = "PICKING_UP"        # Going to customer
    DELIVERING = "DELIVERING"        # Delivering to destination
    ON_BREAK = "ON_BREAK"            # Temporarily unavailable



class DARole(str, Enum):
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"        # Delivering to destination
        # Temporarily unavailable


class DAStatus(str,Enum): 
    ACCEPTED="ACCEPTED"
    PICKED_UP="PICKED_UP"        # Going to customer
    DELIVERED="DELIVERED"        # Delivering to destination
    REJECTED="REJECTED"

class Driver(SQLModel, table=True):
    __tablename__="drivers"
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    user_id: UUID = Field(foreign_key="users.id")
    plate_number: str = Field(sa_column=Column(String(32), nullable=False))
    id_card_number: str = Field(sa_column=Column(String(64), nullable=False))
    vehicle_type: str = Field(sa_column=Column(String(64), nullable=False))
    driver_status: DriverStatus = Field(
        default=DriverStatus.OFFLINE,
        sa_column=Column(SAEnum(DriverStatus, name="driver_status"), nullable=False),
    )
    user: "User" = Relationship(back_populates="driver")
    assignment: "DriverAssignment" = Relationship(back_populates="driver")
    # optional extras
    license_number: str = Field(default=None, sa_column=Column(String(64), nullable=True))
    vehicle_color: str = Field(default=None, sa_column=Column(String(32), nullable=True))

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class DriverAssignment(SQLModel, table=True):
    __tablename__="driver_assignments"
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    driver_id: Optional[UUID] = Field(foreign_key="drivers.id")
    order_id :UUID = Field(foreign_key="orders.id")
    role: DARole | None = Field(
        default=None,
        sa_column=Column(SAEnum(DARole, name="driver_assignment_role"), nullable=True),
    )
    status: DAStatus | None = Field(
        default=None,
        sa_column=Column(SAEnum(DAStatus, name="driver_assignment_status"), nullable=True),
    )
    order: Order= Relationship(back_populates="assignments")
    driver: Driver= Relationship(back_populates="assignment")
    payment: Optional["Payment"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Payment.assignment_id == DriverAssignment.id",
            "foreign_keys": "[Payment.assignment_id]",
            "uselist": False,
        }
    )
    assignedAt: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    deliveryAt: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )



class DriverAssignmentHistory(SQLModel, table=True):
    __tablename__="driver_assignment_histories"
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    driver_id: UUID = Field(foreign_key="drivers.id")
    order_id :UUID = Field(foreign_key="orders.id")
    assignment_id: UUID= Field(foreign_key="driver_assignments.id")
    role: DARole | None = Field(
        default=None,
        sa_column=Column(SAEnum(DARole, name="driver_assignment_role"), nullable=True),
    )
    reason: str | None = Field(default=None, sa_column=Column(String(64), nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
