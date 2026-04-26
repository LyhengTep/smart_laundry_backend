


import decimal

from app.modules.orders.models import Order, OrderItem
from app.modules.orders.schema import OrderCreate
from app.shared.common import generate_order_no


def create_order_factory(data: OrderCreate,subtotal: decimal.Decimal,total: decimal.Decimal,order_item:list[OrderItem])-> dict:
    return Order(
         order_no=generate_order_no(),
        customer_id=data.customer_id,
        business_id=data.business_id,
        pickup_method=data.pickup_method,
        scheduled_pickup_at=data.scheduled_pickup_at,
        scheduled_dropoff_at=data.scheduled_dropoff_at,
        pickup_address=data.pickup_address,
        delivery_address=data.delivery_address,
        notes=data.notes,
        subtotal=subtotal,
        discount=data.discount,
        delivery_fee=0,
        delivery_fee_paid_by=data.delivery_fee_paid_by,
        pickup_latitude=data.pickup_latitude,
        pickup_longitude=data.pickup_longitude,
        delivery_latitude=data.delivery_latitude,
        delivery_longitude=data.delivery_longitude,
        total=total,
        items=order_item,
    )