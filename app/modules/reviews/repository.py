from uuid import UUID

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.modules.reviews.models import ShopReview


async def get_by_id(review_id: UUID, session: AsyncSession) -> ShopReview | None:
    return await session.get(ShopReview, review_id)


async def get_by_business_and_customer(
    business_id: UUID, customer_id: UUID, session: AsyncSession
) -> ShopReview | None:
    result = await session.exec(
        select(ShopReview).where(
            ShopReview.business_id == business_id,
            ShopReview.customer_id == customer_id,
        )
    )
    return result.first()


async def list_by_business(
    business_id: UUID,
    session: AsyncSession,
    page: int = 1,
    size: int = 10,
) -> Page[ShopReview]:
    offset = (page - 1) * size
    statement = (
        select(ShopReview)
        .where(ShopReview.business_id == business_id)
        .order_by(ShopReview.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    count_statement = select(func.count(ShopReview.id)).where(ShopReview.business_id == business_id)

    total = (await session.exec(count_statement)).one()
    reviews = (await session.exec(statement)).all()
    return Page[ShopReview](
        items=list(reviews),
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


async def save(review: ShopReview, session: AsyncSession) -> ShopReview:
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


async def delete(review: ShopReview, session: AsyncSession) -> None:
    await session.delete(review)
    await session.commit()
