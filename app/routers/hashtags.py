from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Hashtag, Ref
from app.dependencies import get_current_user

router = APIRouter(redirect_slashes=False)

@router.get("/")
def get_user_hashtags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 사용자가 사용한 모든 해시태그 조회
    """
    hashtags = db.query(Hashtag).join(Ref.hashtags).filter(
        Ref.user_id == current_user.id
    ).distinct().all()

    return [hashtag.name for hashtag in hashtags]
