


from sqlmodel import SQLModel

from app.modules.users.models import RoleName
from app.modules.users.schema import UserRead, UserWrite


class LoginRequest(SQLModel):
    login: str
    password: str
    role: RoleName


class LoginResponse(UserRead): 
    token: str



class SignupRequest(UserWrite):
    id_number: str | None = None
    vehicle_type: str | None = None
    plate_number: str | None = None
    license_number: str | None = None
    vehicle_color: str | None = None