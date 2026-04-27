from uuid import UUID

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.exceptions.http import create_400, create_404
from app.lib.datetime import utc_now
from app.modules.orders.models import Order, OrderStatus
from app.modules.reviews import repository as repo
from app.modules.reviews.models import ShopReview
from app.modules.reviews.schema import ShopReviewCreate, ShopReviewRead, ShopReviewSummary, ShopReviewUpdate

try:
    from fastapi import HTTPException
    from starlette.status import HTTP_409_CONFLICT

    def create_409(msg: str) -> HTTPException:
        return HTTPException(status_code=HTTP_409_CONFLICT, detail=msg)
except ImportError:
    pass


async def create_review(
    business_id: UUID,
    customer_id: UUID,
    data: ShopReviewCreate,
    session: AsyncSession,
) -> ShopReviewRead:
    order = await session.get(Order, data.order_id)
    if order is None:
        raise create_404("Order not found")

    if order.customer_id != customer_id:
        from app.exceptions.http import create_401
        raise create_401("Order does not belong to you")

    if order.business_id != business_id:
        raise create_400("Order does not belong to this shop")

    if order.status != OrderStatus.DELIVERED:
        raise create_400("You can only review a shop after your order is completed")

    existing = await repo.get_by_order_id(order_id=data.order_id, session=session)
    if existing is not None:
        raise create_409("You have already submitted a review for this order")

    review = ShopReview(
        business_id=business_id,
        customer_id=customer_id,
        order_id=data.order_id,
        rating=data.rating,
        comment=data.comment,
    )
    saved = await repo.save(review=review, session=session)
    return ShopReviewRead.model_validate(saved)


async def list_reviews(
    business_id: UUID,
    session: AsyncSession,
    page: int = 1,
    size: int = 10,
) -> Page[ShopReviewRead]:
    paginated = await repo.list_by_business(
        business_id=business_id, session=session, page=page, size=size
    )
    return Page[ShopReviewRead](
        items=[ShopReviewRead.model_validate(r) for r in paginated.items],
        total=paginated.total,
        page=paginated.page,
        size=paginated.size,
        pages=paginated.pages,
    )


async def get_summary(business_id: UUID, session: AsyncSession) -> ShopReviewSummary:
    result = await session.exec(
        select(
            func.coalesce(func.avg(ShopReview.rating), 0).label("avg_rating"),
            func.count(ShopReview.id).label("total"),
        ).where(ShopReview.business_id == business_id)
    )
    row = result.one()
    return ShopReviewSummary(
        business_id=business_id,
        average_rating=round(float(row.avg_rating), 1),
        total_reviews=row.total,
    )


async def update_review(
    review_id: UUID,
    customer_id: UUID,
    data: ShopReviewUpdate,
    session: AsyncSession,
) -> ShopReviewRead:
    from app.exceptions.http import create_403

    review = await repo.get_by_id(review_id=review_id, session=session)
    if review is None:
        raise create_404("You have not reviewed this shop yet")

    if review.customer_id != customer_id:
        raise create_403("You are not authorized to edit this review")

    if data.rating is not None:
        review.rating = data.rating
    if data.comment is not None:
        review.comment = data.comment
    review.updated_at = utc_now()

    saved = await repo.save(review=review, session=session)
    return ShopReviewRead.model_validate(saved)


async def delete_review(
    review_id: UUID,
    customer_id: UUID,
    session: AsyncSession,
) -> None:
    review = await repo.get_by_id(review_id=review_id, session=session)
    if review is None:
        raise create_404("Review not found")

    if review.customer_id != customer_id:
        from app.exceptions.http import create_401
        raise create_401("You can only delete your own review")

    await repo.delete(review=review, session=session)
