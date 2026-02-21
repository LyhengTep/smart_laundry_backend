

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
    status: UserStatus
    email: str
    phone: str | None
    role: RoleName