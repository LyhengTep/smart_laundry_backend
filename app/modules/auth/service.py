from sqlmodel import select
from app.exceptions.http import  create_404, create_500
from app.modules.auth.schema import LoginRequest,LoginResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import NoResultFound
from app.modules.users.models import User
from app.shared.common import is_email
from app.shared.passwords import create_access_token


async def login(data: LoginRequest, session: AsyncSession)-> LoginResponse:
    response=LoginResponse(token="")
    try:
      user: User
      statement= select(User).where(User.user_name==data.login)
      if is_email(data.login):
        statement=select(User).where(User.email==data.login)
      
      # Query user 
      results=await session.exec(statement)
      user= results.one()

      if user is None:
        raise create_404("Login not found")
      
      token=create_access_token(str(user.id))
      print(f"token is {token}")
      response.token=token
      return response
    except NoResultFound: 
       raise create_404("Login not found")
    except Exception as e: 
       print(f"Unknow error {e}")
       raise create_500("Unknown error occurred")
