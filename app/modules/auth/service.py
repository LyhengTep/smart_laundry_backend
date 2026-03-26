

from sqlmodel import select
from app.exceptions.http import  create_400, create_404, create_500
from app.exceptions.user import UserExistingError
from app.modules.auth.schema import LoginRequest,LoginResponse, SignupRequest
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import NoResultFound
from app.modules.drivers.models import Driver
from app.modules.users.models import RoleName, User, UserStatus
from app.shared.common import is_email
from app.shared.passwords import create_access_token, hash_password


async def login(data: LoginRequest, session: AsyncSession)-> LoginResponse:
    try:
      user: User
      statement= select(User).where(User.user_name==data.login,User.role==data.role)
      if is_email(data.login):
        statement=select(User).where(User.email==data.login,User.role==data.role)
      
      # Query user 
      results=await session.exec(statement)
      user= results.one()

      if user is None:
        raise create_404("Login not found")
      token=create_access_token(str(user.id))

      response=LoginResponse(token=token, **user.model_dump(exclude="password"))
  
      return response
    except NoResultFound: 
       raise create_404("Login not found")
    except Exception as e: 
       print(f"Unknow error {e}")
       raise create_500("Unknown error occurred")



async def signup(data: SignupRequest,session: AsyncSession):
   try:
        statement= select(User).where(User.user_name==data.user_name,User.role==data.role)

        email_statement= select(User).where(User.user_name==data.email,User.role==data.role)
        result= await session.exec(statement)
        emailresult= await session.exec(email_statement)
        print(f"Result exec {result}")
        
        if result.first() or emailresult.first(): 
           raise UserExistingError("User is already existed") 
        driver: Driver
        user= User(
           user_name=data.user_name,
           full_name=data.full_name,
           email=data.email,
           phone=data.phone,
           password_hash=hash_password(data.password),
           role=data.role,
           status= UserStatus.INACTIVE
        )

        session.add(user)
        await session.commit()
        session.refresh(user)

        if data.role==RoleName.DRIVER:
           driver= Driver(
              plate_number=data.plate_number,
              vehicle_color=data.vehicle_color,
              id_card_number=data.id_number,
              vehicle_type=data.vehicle_type,
              user_id=user.id
           )
           session.add(driver)
           await session.commit()
           session.refresh(driver)     

   except UserExistingError:
         raise create_400("Username or email is already taken")
   except Exception:
      session.rollback()
      raise
