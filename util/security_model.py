import bcrypt
import jwt
import datetime
from streamlit import secrets
from typing import Optional
import util.scoring_model as sm

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_token_expire() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=secrets.auth.expire_hours)

def create_token(data: sm.AuthUser) -> str:
    to_encode = dict(data.model_copy())
    expire = get_token_expire()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secrets.auth.key, algorithm=secrets.auth.algorithm)
    return encoded_jwt

def decode_token(token: str) -> Optional[sm.AuthUser]:
    try:
        payload = jwt.decode(token, secrets.auth.key, algorithms=[secrets.auth.algorithm])
        return sm.try_create_authuser(payload)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None