# backend/app/token_cleanup.py

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import RefreshToken, PasswordResetToken


def cleanup_tokens(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    now_naive = now.replace(tzinfo=None)  # DB가 naive datetime을 사용하므로 변환

    # 만료된 Refresh Token 삭제
    expired_refresh = (
        db.query(RefreshToken)
        .filter(RefreshToken.expires_at < now_naive)
        .delete(synchronize_session=False)
    )

    # 만료되었거나 이미 사용된 Password Reset Token 삭제
    expired_reset = (
        db.query(PasswordResetToken)
        .filter(
            (PasswordResetToken.expires_at < now_naive) |
            (PasswordResetToken.used == True)
        )
        .delete(synchronize_session=False)
    )

    db.commit()

    result = {
        "refresh_tokens_deleted": expired_refresh,
        "reset_tokens_deleted": expired_reset,
    }
    print(f"[TokenCleanup] {result}")
    return result
