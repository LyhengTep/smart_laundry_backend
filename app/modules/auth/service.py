

import logging

from sqlalchemy.orm import selectinload
from sqlmodel import select
from app.exceptions.http import  create_400, create_404, create_500
from app.exceptions.user import UserExistingError
from app.modules.auth.schema import LoginRequest,LoginResponse, LogoutRequest, SignupRequest
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import NoResultFound
from app.modules.device_tokens.router import delete_device_token
from app.modules.device_tokens.service import delete_device_tokens_by_user_id
from app.modules.drivers.models import Driver, DriverStatus
from app.modules.users.models import  User, UserStatus
from app.modules.users.schema import UserRead
from app.shared.common import RoleName, is_email
from app.shared.passwords import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)
async def login(data: LoginRequest, session: AsyncSession)-> LoginResponse:
    try:
      user: User
      statement = select(User).where(User.user_name == data.login, User.role == data.role).options(selectinload(User.driver))
      if is_email(data.login):
        statement = select(User).where(User.email == data.login, User.role == data.role)
            # Update Driver status to ONLINE 
      

      results = await session.exec(statement)
      user = results.one()

      if user is None or not verify_password(data.password, user.password_hash):
        raise create_404("Login not found")
      token=create_access_token(str(user.id))

      if data.role==RoleName.DRIVER:
         select_driver= select(Driver).where(Driver.user_id==user.id)
         driver_res = await session.exec(select_driver)
         driver= driver_res.one()
         driver.driver_status= DriverStatus.ONLINE
         if driver is None:
            raise create_404("Driver is not found")
         session.add(driver)
         await session.commit()
         await session.refresh(driver)
         user.driver= driver

      user_data = UserRead.model_validate(user).model_dump(mode="json")
      # print(f"User data {user_data}")
      response=LoginResponse(token=token, **user_data)
  
      return response
    except NoResultFound: 
       raise create_404("Login not found")
    except Exception as e: 
       print(f"Unknow error {e}")
       raise create_500("Unknown error occurred")

async def logout(data: LogoutRequest, session: AsyncSession) -> dict[str, str]:
   user = await session.get(User, data.user_id)
   if user is None:
      raise create_404("User not found")

   user.msg_token = None
   session.add(user)
   await delete_device_tokens_by_user_id(data.user_id, session)
   if data.role == RoleName.DRIVER:
      select_driver = select(Driver).where(Driver.user_id == user.id)
      driver_res = await session.exec(select_driver)
      driver = driver_res.one_or_none()
      if driver is not None:
         driver.driver_status = DriverStatus.OFFLINE
         session.add(driver)

   await session.commit()
   return {"message": "Logout successful"}

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
