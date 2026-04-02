

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlmodel import SQLModel


# from app.modules.auth.schema import DriverBasicRead
from app.modules.users.models import  UserStatus
from app.shared.all_schema import DriverBasicRead
from app.shared.common import RoleName


class UserRead(SQLModel):
    id: UUID
    full_name: str
    user_name: str
    email: str
    phone: str | None
    status: UserStatus
    role: RoleName
    created_at: datetime
    updated_at: datetime
    driver: Optional[DriverBasicRead]= None


class UserWrite(SQLModel):
    full_name: str
    user_name: str
    password: str
    email: str
    phone: str | None
    msg_token: str | None = None
    role: RoleName


class UserEdit(UserWrite):
    status: UserStatus


class UserMsgTokenUpdate(SQLModel):
    msg_token: str | None = None
