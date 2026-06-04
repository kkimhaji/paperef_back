from datetime import datetime, timedelta, timezone
from typing import Optional
from jwt import encode, decode, InvalidTokenError
from pwdlib import PasswordHash
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import os
import secrets
from dotenv import load_dotenv
from app.models import RefreshToken
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()
ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "token_type": "access"})
    return encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({
        "exp": expire,
        "token_type": "refresh",
        "jti": secrets.token_urlsafe(32),
    })
    return encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def save_refresh_token(
    db: Session, user_id: int, token: str, expires_at: datetime
) -> RefreshToken:
    db_token = RefreshToken(token=token, user_id=user_id, expires_at=expires_at)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def verify_refresh_token(db: Session, token: str) -> RefreshToken:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_type") != "refresh":
            raise credentials_exception

        db_token = db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.revoked == False,
        ).first()

        if not db_token:
            raise credentials_exception

        if db_token.expires_at < datetime.utcnow():
            raise credentials_exception

        return db_token

    except InvalidTokenError:
        raise credentials_exception


def revoke_refresh_token(db: Session, token: str) -> bool:
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if db_token:
        db_token.revoked = True
        db.commit()
        return True
    return False


def revoke_all_user_tokens(
    db: Session,
    user_id: int,
    exclude_token: Optional[str] = None,
) -> None:
    """
    Revoke all active refresh tokens for a user.
    exclude_token: if provided, this token is kept active (current session).
    """
    query = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,
    )
    if exclude_token:
        query = query.filter(RefreshToken.token != exclude_token)
    query.update({"revoked": True})
    db.commit()