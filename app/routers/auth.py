from app.models import User, RefreshToken, PasswordResetToken, Group, Ref, Hashtag
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta, datetime
from app.email_service import send_password_reset_email
from app.schemas import (
    UserCreate,
    UserResponse,
    Token,
    TokenRefreshRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChangeRequest,
    DeleteAccountRequest,
    UserStatsResponse,
    UserUpdate,
)
import os
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
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.dependencies import get_current_user

router = APIRouter(redirect_slashes=False)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.username == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email},
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(
        data={"user_id": user.id},
        expires_delta=refresh_token_expires,
    )

    save_refresh_token(db, user.id, refresh_token, datetime.utcnow() + refresh_token_expires)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    token_request: TokenRefreshRequest,
    db: Session = Depends(get_db),
):
    db_token = verify_refresh_token(db, token_request.refresh_token)
    db_token.revoked = True
    db.commit()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    new_access_token = create_access_token(
        data={"user_id": db_token.user_id, "email": db_token.owner.email},
        expires_delta=access_token_expires,
    )
    new_refresh_token = create_refresh_token(
        data={"user_id": db_token.user_id},
        expires_delta=refresh_token_expires,
    )

    save_refresh_token(
        db, db_token.user_id, new_refresh_token, datetime.utcnow() + refresh_token_expires
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(
    token_request: TokenRefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoke_refresh_token(db, token_request.refresh_token)
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoke_all_user_tokens(db, current_user.id)
    return {"message": "Successfully logged out from all devices"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_update.username is not None:
        new_username = user_update.username.strip()
        if not new_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username cannot be empty",
            )
        current_user.username = new_username

    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    request: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
        )

    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete()
    db.delete(current_user)
    db.commit()
    return None


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
            "id":         group.id,
            "name":       group.name,
            "ref_count":  len(group.refs),
            "parent_id":  group.parent_id,
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
        "total_groups":   total_groups,
        "total_refs":     total_refs,
        "total_hashtags": total_hashtags,
        "groups":         group_list,
        "hashtags":       hashtag_list,
    }


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == request.email).first()

    # Do not reveal whether the email exists
    if not user:
        return {"message": "If the email exists, a password reset link has been sent."}

    db.query(PasswordResetToken).filter(
        PasswordResetToken.email == request.email,
        PasswordResetToken.used == False,
    ).delete()

    reset_token = secrets.token_urlsafe(32)
    db_token = PasswordResetToken(
        email=request.email,
        token=reset_token,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(db_token)
    db.commit()

    await send_password_reset_email(request.email, reset_token)

    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token
    ).first()

    if not token_record or not token_record.is_valid():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.email == token_record.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(request.new_password)
    token_record.used = True
    db.commit()

    return {"message": "Password has been reset successfully"}


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    logout_other_devices: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    if logout_other_devices:
        # exclude_token: keep the current session alive after password change
        revoke_all_user_tokens(db, current_user.id, exclude_token=request.refresh_token)
        return {"message": "Password changed successfully. Other devices have been logged out."}

    return {"message": "Password changed successfully."}


@router.get("/open-app")
async def open_app_redirect(token: str):
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")
    web_reset_url = f"{frontend_url}/reset-password?token={token}"
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
            <a href="{deep_link_url}" class="btn">📱 Open in App</a>
            <a href="{web_reset_url}" class="btn-outline">🌐 Reset on Web</a>
            <p class="status" id="statusMsg"></p>
        </div>
        <script>
            window.addEventListener('load', function() {{
                window.location.href = '{deep_link_url}';
                setTimeout(function() {{
                    if (!document.hidden) {{
                        document.getElementById('desc').textContent =
                            'App not installed or not responding.';
                        document.getElementById('statusMsg').textContent =
                            'Use "Reset on Web" if you\\'re not using the app.';
                    }}
                }}, 2500);
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)