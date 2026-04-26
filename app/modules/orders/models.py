from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text
from sqlmodel import Field, Relationship, SQLModel

from app.modules.business_services.model import PriceType
if TYPE_CHECKING:
    from app.modules.drivers.models import DriverAssignment
    from app.modules.users.models import User
    from app.modules.businesses.models import LaundryBusiness
    from app.modules.payments.models import Payment

from app.shared.common import utc_now


class OrderStatus(str, Enum):
    PENDING = "PENDING"                      # Order created, waiting for shop confirmation
    CONFIRMED = "CONFIRMED"                  # Shop accepted order

    PICKUP_ASSIGNED = "PICKUP_ASSIGNED"      # Driver assigned for pickup
    OUT_FOR_PICKUP = "OUT_FOR_PICKUP"        # Driver on the way to customer
    PICKED_UP = "PICKED_UP"                  # Clothes collected from customer
    DELIVERED_TO_SHOP = "DELIVERED_TO_SHOP"  # Clothes delivered to shop

    PROCESSING = "PROCESSING"                # Laundry in progress
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY" # Ready to deliver to customer

    DELIVERY_ASSIGNED = "DELIVERY_ASSIGNED"  # Driver assigned for delivery
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"    # Driver on the way to customer
    PICKED_UP_DELIVERY = "PICKED_UP_DELIVERY"  # Driver picked up clothes from shop for delivery
    DELIVERED = "DELIVERED"                  # Final state

    CANCELLED = "CANCELLED"


class PickupMethod(str, Enum):
    PICKUP = "PICKUP"
    DROP_OFF = "DROP_OFF"


class DeliveryFeePaidBy(str, Enum):
    CUSTOMER = "CUSTOMER"
    SHOP = "SHOP"


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    order_no: str = Field(sa_column=Column(String(32), nullable=False, unique=True, index=True))
    customer_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    business_id: UUID = Field(foreign_key="laundry_businesses.id", nullable=False, index=True)
    driver_id: UUID | None = Field(default=None, foreign_key="drivers.id", nullable=True, index=True)
    status: OrderStatus = Field(
        default=OrderStatus.PENDING,
        sa_column=Column(SAEnum(OrderStatus, name="order_status"), nullable=False, index=True),
    )
    
    pickup_method: PickupMethod = Field(
        sa_column=Column(SAEnum(PickupMethod, name="pickup_method"), nullable=False),
    )
    placed_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    scheduled_pickup_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    scheduled_dropoff_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    pickup_address: str = Field(sa_column=Column(String(255), nullable=False))
    pickup_latitude: float = Field(default=None, sa_column=Column(Float(), nullable=False))
    pickup_longitude: float = Field(default=None, sa_column=Column(Float(), nullable=False))
    delivery_address: str = Field(sa_column=Column(String(255), nullable=False))
    delivery_latitude: float = Field(default=None, sa_column=Column(Float(), nullable=False))
    delivery_longitude: float = Field(default=None, sa_column=Column(Float(), nullable=False))
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    subtotal: float = Field(default=0, sa_column=Column(Float(), nullable=False))
    discount: float = Field(default=0, sa_column=Column(Float(), nullable=False))
    delivery_fee: float = Field(default=0, sa_column=Column(Float(), nullable=False))
    pickup_fee: float = Field(default=0, sa_column=Column(Float(), nullable=False))
    delivery_fee_paid_by: DeliveryFeePaidBy = Field(
        default=DeliveryFeePaidBy.CUSTOMER,
        sa_column=Column(SAEnum(DeliveryFeePaidBy, name="delivery_fee_paid_by"), nullable=False),
    )
    total: float = Field(default=0, sa_column=Column(Float(), nullable=False))
    has_advance_settlement: bool = Field(default=False, sa_column=Column(sa.Boolean(), nullable=False, server_default="false"))
    items: list["OrderItem"] = Relationship(back_populates="order")
    customer: "User" = Relationship(back_populates="orders")
    business: "LaundryBusiness" = Relationship(back_populates="orders")
    assignments: list["DriverAssignment"] = Relationship(back_populates="order")
    payments: list["Payment"] = Relationship(back_populates="order")
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    order_id: UUID = Field(
        sa_column=Column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    business_service_id: UUID = Field(foreign_key="business_services.id", nullable=False, index=True)
    service_id: int = Field(foreign_key="laundry_services.id", nullable=False)
    service_name: str = Field(sa_column=Column(String(100), nullable=False))
    pricing_type: PriceType = Field(
        sa_column=Column(SAEnum(PriceType, name="order_item_price_type"), nullable=False),
    )
    measure_type: str = Field(sa_column=Column(String(30), nullable=False))
    unit_price: float = Field(sa_column=Column(Float(), nullable=False))
    quantity: float = Field(sa_column=Column(Float(), nullable=False))
    sub_total: float = Field(sa_column=Column(Float(), nullable=False))
    note: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    order: "Order" = Relationship(back_populates="items")
