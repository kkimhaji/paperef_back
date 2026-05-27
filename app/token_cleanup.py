from datetime import datetime
from sqlalchemy.orm import Session
from app.models import RefreshToken, PasswordResetToken


def cleanup_tokens(db: Session) -> dict:
    now = datetime.utcnow()

    expired_refresh = (
        db.query(RefreshToken)
        .filter(RefreshToken.expires_at < now)
        .delete(synchronize_session=False)
    )

    expired_reset = (
        db.query(PasswordResetToken)
        .filter(
            (PasswordResetToken.expires_at < now)
            | (PasswordResetToken.used == True)
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