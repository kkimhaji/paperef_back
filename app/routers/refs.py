from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User, Ref, Hashtag, Group
from app.schemas import RefCreate, RefUpdate, RefResponse, RefListResponse
from app.dependencies import get_current_user

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


@router.post("/", response_model=RefResponse, status_code=status.HTTP_201_CREATED)
def create_ref(
        ref_data: RefCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    새로운 논문 메모 생성
    """
    # 논문 생성
    # 그룹 확인
    if ref_data.group_id:
        group = db.query(Group).filter(
            Group.id == ref_data.group_id,
            Group.user_id == current_user.id
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

    new_ref = Ref(
        title=ref_data.title,
        summary=ref_data.summary,
        content=ref_data.content,
        user_id=current_user.id,
        group_id=ref_data.group_id
    )

    # 해시태그 처리
    if ref_data.hashtags:
        for tag_name in ref_data.hashtags:
            hashtag = get_or_create_hashtag(db, tag_name)
            new_ref.hashtags.append(hashtag)

    db.add(new_ref)
    db.commit()
    db.refresh(new_ref)

    return new_ref


@router.get("/", response_model=list[RefListResponse])
def get_refs(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        hashtag: Optional[str] = Query(None, description="Filter by hashtag"),
        group_id: Optional[int] = Query(None, description="Filter by group"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    현재 사용자의 논문 메모 목록 조회
    - hashtag 파라미터로 필터링 가능
    - group_id 파라미터로 그룹별 필터링 가능
    """
    query = db.query(Ref).filter(Ref.user_id == current_user.id)
    # 그룹 필터링
    if group_id is not None:
        if group_id == 0:
            # group_id=0이면 그룹에 속하지 않은 논문들만
            query = query.filter(Ref.group_id == None)
        else:
            # 특정 그룹에 속한 논문들
            query = query.filter(Ref.group_id == group_id)
    # 해시태그 필터링
    if hashtag:
        hashtag = hashtag.strip().lower()
        query = query.join(Ref.hashtags).filter(Hashtag.name == hashtag)

    refs = query.order_by(Ref.updated_at.desc()).offset(skip).limit(limit).all()

    return refs


@router.get("/{ref_id}", response_model=RefResponse)
def get_ref(
        ref_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    특정 논문 메모 상세 조회
    """
    ref = db.query(Ref).filter(
        Ref.id == ref_id,
        Ref.user_id == current_user.id
    ).first()

    if not ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ref not found"
        )

    return ref


@router.put("/{ref_id}", response_model=RefResponse)
def update_ref(
        ref_id: int,
        ref_data: RefUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    논문 메모 수정
    """
    ref = db.query(Ref).filter(
        Ref.id == ref_id,
        Ref.user_id == current_user.id
    ).first()

    if not ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ref not found"
        )
    # 그룹 확인
    if ref_data.group_id is not None:
        if ref_data.group_id > 0:
            group = db.query(Group).filter(
                Group.id == ref_data.group_id,
                Group.user_id == current_user.id
            ).first()
            if not group:
                raise HTTPException(status_code=404, detail="Group not found")
        ref.group_id = ref_data.group_id if ref_data.group_id > 0 else None

    # 필드 업데이트
    if ref_data.title is not None:
        ref.title = ref_data.title
    if ref_data.summary is not None:
        ref.summary = ref_data.summary
    if ref_data.content is not None:
        ref.content = ref_data.content

    # 해시태그 업데이트
    if ref_data.hashtags is not None:
        ref.hashtags.clear()
        for tag_name in ref_data.hashtags:
            hashtag = get_or_create_hashtag(db, tag_name)
            ref.hashtags.append(hashtag)

    db.commit()
    db.refresh(ref)

    return ref


@router.delete("/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ref(
        ref_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    논문 메모 삭제
    """
    ref = db.query(Ref).filter(
        Ref.id == ref_id,
        Ref.user_id == current_user.id
    ).first()

    if not ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ref not found"
        )

    db.delete(ref)
    db.commit()

    return None