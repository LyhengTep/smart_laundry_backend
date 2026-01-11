
from datetime import datetime,timezone,timedelta
import bcrypt
from jose import jwt, JWTError
from app.core.config import JWT_ALGORITHM,JWT_SECRET

def hash_password(pw:str)-> str:
    return bcrypt.hashpw(pw.encode(),bcrypt.gensalt()).decode()



def create_access_token(subject:str)->str:
    expired_duration = datetime.now(timezone.utc) + timedelta(days=7)
    payload={"sub":subject, "exp":expired_duration}
    token= jwt.encode(payload,JWT_SECRET,JWT_ALGORITHM)
    return token
