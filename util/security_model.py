import bcrypt
import jwt
import datetime
from streamlit import secrets
from pydantic import ValidationError
import util.data_model as dm

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_token_expire() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=secrets.auth.expire_hours)

def create_token(data: dm.AuthUser) -> str:
    try:
        to_encode = dict(data.model_copy())
        expire = get_token_expire()
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, secrets.auth.key, algorithm=secrets.auth.algorithm)
        return encoded_jwt
    except Exception as e:
        raise Exception(f"JWT creation error: {e}")

def decode_token(token: str) -> dm.AuthUser | None:
    try:
        payload = jwt.decode(token, secrets.auth.key, algorithms=[secrets.auth.algorithm])
        return dm.AuthUser(**payload)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    except ValidationError as e:
        raise ValidationError(f"JWT decode error: {e}")