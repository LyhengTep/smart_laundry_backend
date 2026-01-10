# app/tests/shared/test_passwords.py
import bcrypt
from app.shared.passwords import hash_password

def test_hash_password_returns_valid_hash():
    password = "P@ssw0rd!"
    hashed = hash_password(password)
    assert bcrypt.checkpw(password.encode(), hashed.encode())
