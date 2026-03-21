from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text
from sqlmodel import Field, Relationship, SQLModel

from app.modules.business_services.model import PriceType
from app.shared.common import utc_now


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PICKED_UP = "PICKED_UP"
    DELIVERED_TO_SHOP = "DELIVERED_TO_SHOP"
    WASHING = "WASHING"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PickupMethod(str, Enum):
    PICKUP = "PICKUP"
    DROP_OFF = "DROP_OFF"


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
    total: float = Field(default=0, sa_column=Column(Float(), nullable=False))
    items: list["OrderItem"] = Relationship(back_populates="order")
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
