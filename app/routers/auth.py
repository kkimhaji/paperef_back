from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from app.email_service import send_password_reset_email
from app.models import User, RefreshToken, PasswordResetToken, Group, Ref, Hashtag
from app.schemas import (
    UserCreate, UserResponse, Token, TokenRefreshRequest,
    PasswordResetRequest, PasswordResetConfirm, PasswordChangeRequest,
    UserStatsResponse
)
import secrets
from app.database import get_db
from app.auth import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, save_refresh_token, verify_refresh_token,
    revoke_refresh_token, revoke_all_user_tokens,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)
from app.dependencies import get_current_user

router = APIRouter()


# ... 기존 엔드포인트들 (register, login, token, refresh, logout 등) ...

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회"""
    return current_user


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """사용자 통계 정보 조회 (그룹 수, 해시태그 수, 레퍼런스 수)"""

    # 그룹 수 (계층 구조 포함 모든 그룹)
    total_groups = db.query(Group).filter(Group.user_id == current_user.id).count()

    # 레퍼런스 수
    total_refs = db.query(Ref).filter(Ref.user_id == current_user.id).count()

    # 사용자의 레퍼런스에 연결된 고유 해시태그 수
    hashtag_ids = db.query(Hashtag.id).join(
        Ref.hashtags
    ).filter(
        Ref.user_id == current_user.id
    ).distinct().all()
    total_hashtags = len(hashtag_ids)

    # 그룹 목록 (최대 10개, ref_count 포함)
    groups = db.query(Group).filter(
        Group.user_id == current_user.id
    ).order_by(Group.name).limit(10).all()

    group_list = [
        {
            "id": group.id,
            "name": group.name,
            "ref_count": len(group.refs),
            "parent_id": group.parent_id
        }
        for group in groups
    ]

    # 해시태그 목록 (최대 10개, 사용 빈도순)
    hashtag_usage = db.query(
        Hashtag.name,
        db.func.count(Ref.id).label('count')
    ).join(
        Ref.hashtags
    ).filter(
        Ref.user_id == current_user.id
    ).group_by(
        Hashtag.name
    ).order_by(
        db.func.count(Ref.id).desc()
    ).limit(10).all()

    hashtag_list = [
        {"name": tag.name, "count": tag.count}
        for tag in hashtag_usage
    ]

    return {
        "total_groups": total_groups,
        "total_refs": total_refs,
        "total_hashtags": total_hashtags,
        "groups": group_list,
        "hashtags": hashtag_list
    }


@router.post("/change-password")
async def change_password(
        request: PasswordChangeRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """비밀번호 변경 (현재 비밀번호 확인 필요)"""

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

    # 모든 기기에서 로그아웃 (보안을 위해)
    revoke_all_user_tokens(db, current_user.id)

    return {"message": "Password changed successfully. Please login again."}


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
