import hashlib
import secrets

from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(psw: str) -> str:
    return pwd_context.hash(psw)

def verify_password(plain_psw: str, hashed_psw: str) -> bool:
    return pwd_context.verify(plain_psw, hashed_psw)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def get_refresh_token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=30)
