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

load_dotenv()

# 환경 변수
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

password_hash = PasswordHash.recommended()


# 비밀번호 해싱 및 검증
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


# JWT Access Token 생성
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "token_type": "access"})
    encoded_jwt = encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# JWT Refresh Token 생성
def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # 추가 보안을 위해 랜덤 jti (JWT ID) 추가
    to_encode.update({
        "exp": expire,
        "token_type": "refresh",
        "jti": secrets.token_urlsafe(32)
    })
    encoded_jwt = encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Refresh Token을 데이터베이스에 저장
def save_refresh_token(db: Session, user_id: int, token: str, expires_at: datetime) -> RefreshToken:
    db_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


# Refresh Token 검증 및 조회
def verify_refresh_token(db: Session, token: str) -> RefreshToken:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type: str = payload.get("token_type")

        if token_type != "refresh":
            raise credentials_exception

        # 데이터베이스에서 토큰 확인
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.revoked == False
        ).first()

        if not db_token:
            raise credentials_exception

        # 만료 확인
        if db_token.expires_at < datetime.utcnow():
            raise credentials_exception

        return db_token

    except InvalidTokenError:
        raise credentials_exception

# Refresh Token 무효화 (로그아웃 시 사용)
def revoke_refresh_token(db: Session, token: str) -> bool:
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if db_token:
        db_token.revoked = True
        db.commit()
        return True
    return False


# 사용자의 모든 Refresh Token 무효화 (전체 로그아웃)
def revoke_all_user_tokens(db: Session, user_id: int):
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    ).update({"revoked": True})
    db.commit()