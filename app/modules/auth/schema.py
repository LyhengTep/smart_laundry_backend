


from sqlmodel import SQLModel


class LoginRequest(SQLModel):
    login: str
    password: str


class LoginResponse(SQLModel): 
    token: str