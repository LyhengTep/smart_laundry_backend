
import bcrypt


def hash_password(pw:str)-> str:
    return bcrypt.hashpw(pw.encode(),bcrypt.gensalt()).decode()