from datetime import datetime
from uuid import UUID

from pydantic import field_validator, model_validator
from sqlmodel import SQLModel

from app.shared.all_schema import UserReadBasicRead




class ShopReviewCreate(SQLModel):
    rating: int
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 500:
            raise ValueError("Comment must not exceed 500 characters")
        return v


class ShopReviewUpdate(SQLModel):
    rating: int | None = None
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 500:
            raise ValueError("Comment must not exceed 500 characters")
        return v

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "ShopReviewUpdate":
        if self.rating is None and self.comment is None:
            raise ValueError("At least one of rating or comment must be provided")
        return self


class ShopReviewRead(SQLModel):
    id: UUID
    business_id: UUID
    customer_id: UUID
    rating: int
    comment: str | None
    customer: UserReadBasicRead | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ShopReviewSummary(SQLModel):
    business_id: UUID
    average_rating: float
    total_reviews: int
