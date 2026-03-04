from app.models import User, RefreshToken, PasswordResetToken, Group, Ref, Hashtag
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta, datetime, timezone
from app.email_service import send_password_reset_email
from app.schemas import (
    UserCreate,
    UserResponse,
    Token,
    TokenRefreshRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChangeRequest,
    UserStatsResponse,
    UserUpdate
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

router = APIRouter(redirect_slashes=False)


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


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회"""
    return current_user


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_groups = db.query(Group).filter(Group.user_id == current_user.id).count()
    total_refs = db.query(Ref).filter(Ref.user_id == current_user.id).count()

    hashtag_ids = (
        db.query(Hashtag.id)
        .join(Ref.hashtags)
        .filter(Ref.user_id == current_user.id)
        .distinct()
        .all()
    )
    total_hashtags = len(hashtag_ids)

    groups = (
        db.query(Group)
        .filter(Group.user_id == current_user.id)
        .order_by(Group.name)
        .limit(10)
        .all()
    )
    group_list = [
        {
            "id": group.id,
            "name": group.name,
            "ref_count": len(group.refs),
            "parent_id": group.parent_id,
            "created_at": group.created_at,
            "updated_at": group.updated_at,
        }
        for group in groups
    ]

    hashtag_usage = (
        db.query(Hashtag.name, func.count(Ref.id).label("count"))
        .join(Ref.hashtags)
        .filter(Ref.user_id == current_user.id)
        .group_by(Hashtag.name)
        .order_by(func.count(Ref.id).desc())
        .limit(10)
        .all()
    )
    hashtag_list = [{"name": tag.name, "count": tag.count} for tag in hashtag_usage]

    return {
        "total_groups": total_groups,
        "total_refs": total_refs,
        "total_hashtags": total_hashtags,
        "groups": group_list,
        "hashtags": hashtag_list,
    }



@router.post("/change-password")
async def change_password(
        request: PasswordChangeRequest,
        logout_other_devices: bool = True,  # 쿼리 파라미터
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """비밀번호 변경"""

    # 현재 비밀번호 확인
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # 새 비밀번호와 현재 비밀번호가 같은지 확인
    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    # 비밀번호 업데이트
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    # 사용자 선택에 따라 다른 기기 로그아웃
    if logout_other_devices:
        revoke_all_user_tokens(db, current_user.id)
        return {
            "message": "Password changed successfully. Other devices have been logged out."
        }
    else:
        return {
            "message": "Password changed successfully."
        }


@router.put("/me", response_model=UserResponse)
async def update_me(
        user_update: UserUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    if user_update.username is not None:
        new_username = user_update.username.strip()

        # 빈 문자열 체크만 (Pydantic에서 이미 1글자 이상 보장)
        if not new_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username cannot be empty",
            )

        # Unique 체크만 (길이는 Pydantic 스키마에서 처리)
        existing = (
            db.query(User)
            .filter(User.username == new_username, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        current_user.username = new_username

    db.commit()
    db.refresh(current_user)
    return current_user

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
        password: str,  # Query parameter로 비밀번호 받기
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """계정 탈퇴 (비밀번호 확인 필요)

    - 모든 레퍼런스 삭제
    - 모든 그룹 삭제
    - 모든 토큰 삭제
    - 사용자 계정 삭제
    """

    # 비밀번호 확인
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    # 모든 리프레시 토큰 삭제
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete()

    # 모든 레퍼런스 삭제 (cascade로 자동 삭제됨)
    # 모든 그룹 삭제 (cascade로 자동 삭제됨)

    # 사용자 삭제 (cascade로 모든 관련 데이터 삭제)
    db.delete(current_user)
    db.commit()

    return None


@router.post("/forgot-password")
async def forgot_password(
        request: PasswordResetRequest,
        db: Session = Depends(get_db)
):
    """비밀번호 재설정 이메일 전송"""
    # 기존 코드 유지
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        return {"message": "If the email exists, a password reset link has been sent."}

    # 기존 미사용 토큰 삭제
    db.query(PasswordResetToken).filter(
        PasswordResetToken.email == request.email,
        PasswordResetToken.used == False
    ).delete()

    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    db_token = PasswordResetToken(
        email=request.email,
        token=reset_token,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()

    await send_password_reset_email(request.email, reset_token)

    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(
        request: PasswordResetConfirm,
        db: Session = Depends(get_db)
):
    """비밀번호 재설정 (토큰 기반)"""
    # 기존 코드 유지
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token
    ).first()

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if not token_record.is_valid():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.email == token_record.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(request.new_password)
    token_record.used = True
    db.commit()

    return {"message": "Password has been reset successfully"}


@router.get("/open-app")
async def open_app_redirect(token: str):
    import os
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")
    web_reset_url = f"{frontend_url}/reset-password?token={token}"
    # host를 "app"으로, path를 "/reset-password"로 명확히 분리
    deep_link_url = f"paperef://app/reset-password?token={token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Paperef - Password Reset</title>
        <style>
            body {{
                font-family: 'Segoe UI', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background-color: #f5f5f5;
            }}
            .card {{
                background: white;
                border-radius: 12px;
                padding: 40px;
                max-width: 400px;
                width: 90%;
                text-align: center;
                box-shadow: 0 2px 16px rgba(0,0,0,0.1);
            }}
            .icon {{ font-size: 48px; margin-bottom: 16px; }}
            h2 {{ color: #528155; margin-bottom: 8px; }}
            p {{ color: #666; margin-bottom: 24px; }}
            .btn {{
                display: block;
                padding: 14px 32px;
                background-color: #528155;
                color: white !important;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 16px;
                margin-bottom: 12px;
                box-sizing: border-box;
            }}
            .btn-outline {{
                display: block;
                padding: 14px 32px;
                background-color: white;
                color: #528155 !important;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 16px;
                border: 2px solid #528155;
                box-sizing: border-box;
            }}
            .status {{ color: #999; font-size: 13px; margin-top: 16px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">🔐</div>
            <h2>Reset Your Password</h2>
            <p id="desc">Trying to open the Paperef app...</p>

            <a href="{deep_link_url}" class="btn" id="openAppBtn">📱 Open in App</a>
            <a href="{web_reset_url}" class="btn-outline">🌐 Reset on Web</a>

            <p class="status" id="statusMsg"></p>
        </div>

        <script>
            window.addEventListener('load', function() {{
                var deepLink = '{deep_link_url}';
                var webFallback = '{web_reset_url}';
                var clicked = false;

                // 자동으로 딥링크 시도
                window.location.href = deepLink;

                // 페이지가 여전히 포커스를 갖고 있으면 앱이 없는 것
                setTimeout(function() {{
                    if (!document.hidden) {{
                        document.getElementById('desc').textContent =
                            'App not installed or not responding.';
                        document.getElementById('statusMsg').textContent =
                            'Use "Reset on Web" if you\'re not using the app.';
                    }}
                }}, 2500);
            }});
        </script>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)
