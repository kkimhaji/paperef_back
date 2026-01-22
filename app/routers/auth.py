from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from app.email_service import send_password_reset_email
from app.models import User, RefreshToken, PasswordResetToken
from app.schemas import (
    UserCreate,
    UserResponse,
    Token,
    TokenRefreshRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
)
import secrets
from app.database import get_db
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    save_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    새로운 사용자 등록
    """
    # 이메일 중복 확인
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # 사용자명 중복 확인
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # 새 사용자 생성
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/token", response_model=Token)
def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """
    로그인 (JWT Access Token + Refresh Token 발급)
    - username 필드에 email 또는 username을 입력
    """
    # 이메일 또는 사용자명으로 사용자 찾기
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.username == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Access Token 생성 (15분)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email},
        expires_delta=access_token_expires
    )

    # Refresh Token 생성 (7일)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"user_id": user.id},
        expires_delta=refresh_token_expires
    )

    # Refresh Token을 데이터베이스에 저장
    expires_at = datetime.now(timezone.utc) + refresh_token_expires
    save_refresh_token(db, user.id, refresh_token, expires_at)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
def refresh_access_token(
        token_request: TokenRefreshRequest,
        db: Session = Depends(get_db)
):
    """
    Refresh Token을 사용하여 새로운 Access Token 발급
    - Refresh Token도 갱신됨 (Token Rotation)
    """
    # Refresh Token 검증
    db_token = verify_refresh_token(db, token_request.refresh_token)

    # 기존 Refresh Token 무효화 (Token Rotation)
    db_token.revoked = True
    db.commit()

    # 새로운 Access Token 생성 (15분)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"user_id": db_token.user_id, "email": db_token.owner.email},
        expires_delta=access_token_expires
    )

    # 새로운 Refresh Token 생성 (7일)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = create_refresh_token(
        data={"user_id": db_token.user_id},
        expires_delta=refresh_token_expires
    )

    # 새 Refresh Token을 데이터베이스에 저장
    expires_at = datetime.now(timezone.utc) + refresh_token_expires
    save_refresh_token(db, db_token.user_id, new_refresh_token, expires_at)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(
        token_request: TokenRefreshRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    로그아웃 (Refresh Token 무효화)
    """
    revoke_refresh_token(db, token_request.refresh_token)
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
def logout_all_devices(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    모든 기기에서 로그아웃 (사용자의 모든 Refresh Token 무효화)
    """
    revoke_all_user_tokens(db, current_user.id)
    return {"message": "Successfully logged out from all devices"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    현재 로그인한 사용자 정보 조회
    """
    return current_user


@router.post("/forgot-password")
async def forgot_password(
        request: PasswordResetRequest,
        db: Session = Depends(get_db)
):
    """
    비밀번호 재설정 요청 - 이메일로 재설정 링크 전송
    """
    # 이메일이 존재하는지 확인
    user = db.query(User).filter(User.email == request.email).first()

    # 보안상 이메일 존재 여부를 알려주지 않음
    if not user:
        return {"message": "If the email exists, a password reset link has been sent."}

    # 기존 토큰이 있으면 삭제
    db.query(PasswordResetToken).filter(
        PasswordResetToken.email == request.email,
        PasswordResetToken.used == False
    ).delete()

    # 재설정 토큰 생성
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    # 토큰 저장
    db_token = PasswordResetToken(
        email=request.email,
        token=reset_token,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()

    # 이메일 전송
    await send_password_reset_email(request.email, reset_token)

    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(
        request: PasswordResetConfirm,
        db: Session = Depends(get_db)
):
    """
    비밀번호 재설정 확인 - 토큰 검증 후 새 비밀번호 설정
    """
    # 토큰 조회
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token
    ).first()

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # 토큰 유효성 검사
    if not token_record.is_valid():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # 사용자 조회
    user = db.query(User).filter(User.email == token_record.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 비밀번호 변경
    user.hashed_password = get_password_hash(request.new_password)

    # 토큰 사용 처리
    token_record.used = True

    db.commit()

    return {"message": "Password has been reset successfully"}