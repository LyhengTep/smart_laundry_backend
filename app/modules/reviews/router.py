from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status

from app.api.reponse_model import Page
from app.db.engine import get_session
from app.lib.security import get_current_user
from app.modules.reviews import service as svc
from app.modules.reviews.schema import ShopReviewCreate, ShopReviewRead, ShopReviewSummary, ShopReviewUpdate
from app.modules.users.models import User

router = APIRouter(prefix="/businesses/{business_id}/reviews", tags=["reviews"])


@router.post("", response_model=ShopReviewRead, status_code=status.HTTP_201_CREATED)
async def submit_review(
    business_id: UUID,
    data: ShopReviewCreate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ShopReviewRead:
    return await svc.create_review(
        business_id=business_id,
        customer_id=UUID(current_user),
        data=data,
        session=session,
    )


@router.get("", response_model=Page[ShopReviewRead])
async def list_reviews(
    business_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> Page[ShopReviewRead]:
    return await svc.list_reviews(business_id=business_id, session=session, page=page, size=size)


@router.get("/summary", response_model=ShopReviewSummary)
async def get_summary(
    business_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ShopReviewSummary:
    return await svc.get_summary(business_id=business_id, session=session)


@router.patch("/{review_id}", response_model=ShopReviewRead)
async def update_review(
    business_id: UUID,
    review_id: UUID,
    data: ShopReviewUpdate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ShopReviewRead:
    return await svc.update_review(
        review_id=review_id,
        customer_id=UUID(current_user),
        data=data,
        session=session,
    )


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    business_id: UUID,
    review_id: UUID,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await svc.delete_review(
        review_id=review_id,
        customer_id=UUID(current_user),
        session=session,
    )
