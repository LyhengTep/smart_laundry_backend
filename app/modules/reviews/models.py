from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.lib.datetime import utc_now

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.businesses.models import LaundryBusiness
    from app.modules.orders.models import Order


class ShopReview(SQLModel, table=True):
    __tablename__ = "shop_reviews"
    __table_args__ = (UniqueConstraint("order_id", name="uq_shop_review_order"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    business_id: UUID = Field(sa_column=Column(ForeignKey("laundry_businesses.id", ondelete="CASCADE"), nullable=False))
    customer_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    order_id: UUID = Field(sa_column=Column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True))
    rating: int = Field(sa_column=Column(Integer(), nullable=False))
    comment: Optional[str] = Field(default=None, sa_column=Column(Text(), nullable=True))
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))

    business: Optional["LaundryBusiness"] = Relationship()
    customer: Optional["User"] = Relationship()
    order: Optional["Order"] = Relationship()
