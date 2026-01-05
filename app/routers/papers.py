from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User, Paper, Hashtag
from app.schemas import PaperCreate, PaperUpdate, PaperResponse, PaperListResponse
from app.auth import get_current_user

router = APIRouter()


def get_or_create_hashtag(db: Session, hashtag_name: str) -> Hashtag:
    """
    해시태그 조회 또는 생성
    """
    hashtag_name = hashtag_name.strip().lower()
    hashtag = db.query(Hashtag).filter(Hashtag.name == hashtag_name).first()
    if not hashtag:
        hashtag = Hashtag(name=hashtag_name)
        db.add(hashtag)
        db.commit()
        db.refresh(hashtag)
    return hashtag


@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
def create_paper(
        paper_data: PaperCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    새로운 논문 메모 생성
    """
    # 논문 생성
    new_paper = Paper(
        title=paper_data.title,
        summary=paper_data.summary,
        content=paper_data.content,
        user_id=current_user.id
    )

    # 해시태그 처리
    if paper_data.hashtags:
        for tag_name in paper_data.hashtags:
            hashtag = get_or_create_hashtag(db, tag_name)
            new_paper.hashtags.append(hashtag)

    db.add(new_paper)
    db.commit()
    db.refresh(new_paper)

    return new_paper


@router.get("/", response_model=list[PaperListResponse])
def get_papers(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        hashtag: Optional[str] = Query(None, description="Filter by hashtag"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    현재 사용자의 논문 메모 목록 조회
    - hashtag 파라미터로 필터링 가능
    """
    query = db.query(Paper).filter(Paper.user_id == current_user.id)

    # 해시태그 필터링
    if hashtag:
        hashtag = hashtag.strip().lower()
        query = query.join(Paper.hashtags).filter(Hashtag.name == hashtag)

    papers = query.order_by(Paper.updated_at.desc()).offset(skip).limit(limit).all()

    return papers


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(
        paper_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    특정 논문 메모 상세 조회
    """
    paper = db.query(Paper).filter(
        Paper.id == paper_id,
        Paper.user_id == current_user.id
    ).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )

    return paper


@router.put("/{paper_id}", response_model=PaperResponse)
def update_paper(
        paper_id: int,
        paper_data: PaperUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    논문 메모 수정
    """
    paper = db.query(Paper).filter(
        Paper.id == paper_id,
        Paper.user_id == current_user.id
    ).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )

    # 필드 업데이트
    if paper_data.title is not None:
        paper.title = paper_data.title
    if paper_data.summary is not None:
        paper.summary = paper_data.summary
    if paper_data.content is not None:
        paper.content = paper_data.content

    # 해시태그 업데이트
    if paper_data.hashtags is not None:
        paper.hashtags.clear()
        for tag_name in paper_data.hashtags:
            hashtag = get_or_create_hashtag(db, tag_name)
            paper.hashtags.append(hashtag)

    db.commit()
    db.refresh(paper)

    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
        paper_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    논문 메모 삭제
    """
    paper = db.query(Paper).filter(
        Paper.id == paper_id,
        Paper.user_id == current_user.id
    ).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )

    db.delete(paper)
    db.commit()

    return None


@router.get("/hashtags/all", response_model=list[str])
def get_user_hashtags(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    현재 사용자가 사용한 모든 해시태그 조회
    """
    hashtags = db.query(Hashtag).join(Paper.hashtags).filter(
        Paper.user_id == current_user.id
    ).distinct().all()

    return [hashtag.name for hashtag in hashtags]