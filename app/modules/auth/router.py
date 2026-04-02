


from urllib import response
from fastapi import APIRouter, Depends

from app.db.engine import get_session
from app.modules.auth.schema import LoginRequest, LoginResponse, LogoutRequest, SignupRequest
from app.modules.auth import service as svc
from sqlmodel.ext.asyncio.session import AsyncSession
router = APIRouter(prefix="/auths",tags=["auth"])


@router.post("/login")
async def login(login: LoginRequest,session: AsyncSession=Depends(get_session))-> LoginResponse:
    response = await svc.login(login,session)
    return response

@router.post("/signup")
async def signup(data: SignupRequest,session: AsyncSession=Depends(get_session))-> dict[str, str]:

    response = await svc.signup(data,session)
    return {"msg": "World"}


@router.post("/password-reset")
async def password_reset()-> dict[str, str]:

    
    return {"msg": "World"}

@router.post("/logout")
async def logout(data: LogoutRequest, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    return await svc.logout(data=data, session=session)
