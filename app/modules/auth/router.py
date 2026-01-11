


from fastapi import APIRouter, Depends

from app.db.engine import get_session
from app.modules.auth.schema import LoginRequest, LoginResponse
from app.modules.auth import service as svc
from sqlmodel.ext.asyncio.session import AsyncSession
router = APIRouter(prefix="/auths",tags=["auth"])


@router.post("/login")
async def login(login: LoginRequest,session: AsyncSession=Depends(get_session))-> LoginResponse:
    response = await svc.login(login,session)
    return response

@router.post("/register")
async def register()-> dict[str, str]:
    return {"msg": "World"}


@router.post("/password-reset")
async def password_reset()-> dict[str, str]:
    return {"msg": "World"}

# @router.post("/logout")
# async def login()-> dict[str, str]:
#     return {"msg": "World"}