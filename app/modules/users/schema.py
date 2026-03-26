

from datetime import datetime
import email
from uuid import UUID
from sqlmodel import SQLModel

from app.modules.users.models import RoleName, UserStatus


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
