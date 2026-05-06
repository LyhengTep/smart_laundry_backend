import logging

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.exceptions.http import create_400, create_404, create_500
from app.exceptions.user import UserExistingError
from app.modules.auth.schema import LoginRequest, LoginResponse, LogoutRequest, SignupRequest
from app.modules.device_tokens.service import delete_device_tokens_by_user_id
from app.modules.drivers.models import Driver, DriverStatus
from app.modules.users.models import User, UserStatus
from app.modules.users import repository as user_repo
from app.modules.users.schema import UserRead
from app.shared.common import RoleName, is_email
from app.shared.passwords import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)


async def login(data: LoginRequest, session: AsyncSession) -> LoginResponse:
   """Authenticate a user by username/email + password. Sets driver status ONLINE on success."""
   try:
      if is_email(data.login):
         user = await user_repo.get_by_email_and_role(data.login, data.role, session)
      else:
         user = await user_repo.get_by_username_and_role(data.login, data.role, session)

      if user is None or not verify_password(data.password, user.password_hash):
         raise create_404("Login not found")
      if user.status != UserStatus.ACTIVE:
         raise create_400(f"Account is {user.status.value.lower()}. Please contact support.")

      token = create_access_token(str(user.id))

      if data.role == RoleName.DRIVER:
         result = await session.exec(select(Driver).where(Driver.user_id == user.id))
         driver = result.one_or_none()
         if driver is None:
            raise create_404("Driver is not found")
         driver.driver_status = DriverStatus.ONLINE
         session.add(driver)
         await session.commit()
         await session.refresh(driver)
         user.driver = driver

      user_data = UserRead.model_validate(user).model_dump(mode="json")
      return LoginResponse(token=token, **user_data)

   except HTTPException:
      raise
   except NoResultFound:
      raise create_404("Login not found")
   except Exception as e:
      print(f"Unknow error {e}")
      raise create_500("Unknown error occurred")


async def logout(data: LogoutRequest, session: AsyncSession) -> dict[str, str]:
   """Clear msg_token and device tokens; set driver status OFFLINE if role is DRIVER."""
   user = await user_repo.get_by_id(data.user_id, session)
   if user is None:
      raise create_404("User not found")

   user.msg_token = None
   session.add(user)
   await delete_device_tokens_by_user_id(data.user_id, session)

   if data.role == RoleName.DRIVER:
      result = await session.exec(select(Driver).where(Driver.user_id == user.id))
      driver = result.one_or_none()
      if driver is not None:
         driver.driver_status = DriverStatus.OFFLINE
         session.add(driver)

   await session.commit()
   return {"message": "Logout successful"}


async def signup(data: SignupRequest, session: AsyncSession):
   """Register a new user (INACTIVE by default); creates a linked Driver record if role is DRIVER."""
   try:
      existing = await user_repo.get_by_username_and_role(data.user_name, data.role, session)
      existing_email = await user_repo.get_by_email_and_role(data.email, data.role, session)
      if existing or existing_email:
         raise UserExistingError("User is already existed")

      user = User(
         user_name=data.user_name,
         full_name=data.full_name,
         email=data.email,
         phone=data.phone,
         password_hash=hash_password(data.password),
         role=data.role,
         status=UserStatus.INACTIVE,
      )
      session.add(user)
      await session.commit()
      session.refresh(user)

      if data.role == RoleName.DRIVER:
         driver = Driver(
            plate_number=data.plate_number,
            vehicle_color=data.vehicle_color,
            id_card_number=data.id_number,
            vehicle_type=data.vehicle_type,
            user_id=user.id,
         )
         session.add(driver)
         await session.commit()
         session.refresh(driver)

   except UserExistingError:
      raise create_400("Username or email is already taken")
   except Exception:
      await session.rollback()
      raise
