from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel

from app.modules.business_services.model import PriceType
from app.modules.businesses.schema import BusinessRead
from app.modules.orders.models import OrderStatus, PickupMethod
from app.modules.users.schema import UserRead
from app.shared.all_schema import UserReadBasicRead


class OrderCreateItem(SQLModel):
    business_service_id: UUID
    quantity: float | None = None
    note: str | None = None


class OrderCreate(SQLModel):
    customer_id: UUID
    business_id: UUID
    pickup_method: PickupMethod
    pickup_address: str
    delivery_address: str
    notes: str | None = None
    discount: float = 0
    scheduled_pickup_at: datetime | None = None
    scheduled_dropoff_at: datetime | None = None
    pickup_latitude: float
    pickup_longitude: float
    delivery_latitude: float
    delivery_longitude: float
    items: list[OrderCreateItem]


class OrderItemRead(SQLModel):
    id: UUID
    business_service_id: UUID
    service_id: int
    service_name: str
    pricing_type: PriceType
    measure_type: str
    unit_price: float
    quantity: float
    sub_total: float
    note: str | None


class OrderRead(SQLModel):
    id: UUID
    order_no: str
    customer_id: UUID
    business_id: UUID
    driver_id: UUID | None
    status: OrderStatus
    pickup_method: PickupMethod
    placed_at: datetime
    scheduled_pickup_at: datetime | None
    scheduled_dropoff_at: datetime | None
    pickup_address: str
    pickup_latitude: float
    pickup_longitude: float
    delivery_address: str
    delivery_latitude: float
    delivery_longitude: float
    notes: str | None
    subtotal: float
    discount: float
    total: float
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]
    customer: UserReadBasicRead | None
    model_config = {"from_attributes": True}



class OrderReadV2(OrderRead):
    customer: UserRead | None
    business: BusinessRead | None
    model_config = {"from_attributes": True}


class OrderStatusUpdate(SQLModel):
    status: OrderStatus
    driver_id: UUID | None = None


class OrderPricingItemUpdate(SQLModel):
    order_item_id: UUID
    quantity: float


class OrderPricingUpdate(SQLModel):
    items: list[OrderPricingItemUpdate]
    discount: float | None = None
