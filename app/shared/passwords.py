
from datetime import datetime,timezone,timedelta
import logging
import bcrypt
from jose import jwt, JWTError
from app.core.config import JWT_ALGORITHM,JWT_SECRET



from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer

from app.exceptions.http import create_401


security = HTTPBearer()



def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        logging.info(f"Decoded JWT payload: {payload}")
        if user_id is None:
            raise create_401()
        return user_id
    except JWTError:
        raise create_401()
    



def hash_password(pw:str)-> str:
    return bcrypt.hashpw(pw.encode(),bcrypt.gensalt()).decode()



def create_access_token(subject:str)->str:
    expired_duration = datetime.now(timezone.utc) + timedelta(days=7)
    payload={"sub":subject, "exp":expired_duration}
    token= jwt.encode(payload,JWT_SECRET,JWT_ALGORITHM)
    return token
