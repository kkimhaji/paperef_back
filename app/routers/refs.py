from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.database import get_db
from app.models import User, Ref, Hashtag, Group
from app.schemas import RefCreate, RefUpdate, RefResponse, RefListResponse
from app.dependencies import get_current_user

router = APIRouter()


def get_or_create_hashtag(db: Session, hashtag_name: str) -> Hashtag:
    """해시태그 조회 또는 생성"""
    hashtag_name = hashtag_name.strip().lower()
    hashtag = db.query(Hashtag).filter(Hashtag.name == hashtag_name).first()
    if not hashtag:
        hashtag = Hashtag(name=hashtag_name)
        db.add(hashtag)
        db.commit()
        db.refresh(hashtag)
    return hashtag


def get_all_descendant_group_ids(db: Session, group_id: int) -> List[int]:
    """
    재귀적으로 모든 하위 그룹의 ID를 수집

    Args:
        db: 데이터베이스 세션
        group_id: 시작 그룹 ID

    Returns:
        List[int]: 해당 그룹과 모든 하위 그룹의 ID 리스트
    """
    group_ids = [group_id]

    # 직접 자식 그룹 조회
    children = db.query(Group).filter(Group.parent_id == group_id).all()

    # 재귀적으로 각 자식의 하위 그룹 ID 수집
    for child in children:
        group_ids.extend(get_all_descendant_group_ids(db, child.id))

    return group_ids


def get_group_path(db: Session, group_id: int) -> str:
    """그룹의 전체 경로를 '/' 구분자로 반환

    예시:
    - Root Group -> "Root Group"
    - Sub Group (parent: Root Group) -> "Root Group / Sub Group"
    - Deep Group (parent: Sub Group) -> "Root Group / Sub Group / Deep Group"
    """
    path_parts = []
    current = db.query(Group).filter(Group.id == group_id).first()

    while current:
        path_parts.insert(0, current.name)
        if current.parent_id:
            current = db.query(Group).filter(Group.id == current.parent_id).first()
        else:
            current = None

    return " / ".join(path_parts)

@router.post("/", response_model=RefResponse, status_code=status.HTTP_201_CREATED)
def create_ref(
        ref_data: RefCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """레퍼런스 생성"""
    # 그룹 존재 확인
    if ref_data.group_id:
        group = db.query(Group).filter(
            Group.id == ref_data.group_id,
            Group.user_id == current_user.id,
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

    new_ref = Ref(
        title=ref_data.title,
        summary=ref_data.summary,
        content=ref_data.content,
        user_id=current_user.id,
        group_id=ref_data.group_id,
    )

    # 해시태그 추가
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
        limit: int = Query(100, ge=1, le=100),
        hashtag: Optional[str] = Query(None, description="Filter by hashtag"),
        group_id: Optional[int] = Query(None, description="Filter by group (includes subgroups)"),
        search: Optional[str] = Query(None, description="Search in title, summary, and content"),
        include_subgroups: bool = Query(True, description="Include references from subgroups"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """레퍼런스 목록 조회 (그룹 경로 포함)"""
    query = db.query(Ref).options(
        joinedload(Ref.group),
        joinedload(Ref.hashtags)
    ).filter(Ref.user_id == current_user.id)

    if group_id is not None:
        if group_id == 0:
            query = query.filter(Ref.group_id == None)
        else:
            if include_subgroups:
                all_group_ids = get_all_descendant_group_ids(db, group_id)
                query = query.filter(Ref.group_id.in_(all_group_ids))
            else:
                query = query.filter(Ref.group_id == group_id)

    if hashtag:
        hashtag = hashtag.strip().lower()
        query = query.join(Ref.hashtags).filter(Hashtag.name == hashtag)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Ref.title.ilike(search_pattern)) |
            (Ref.summary.ilike(search_pattern)) |
            (Ref.content.ilike(search_pattern))
        )

    refs = query.order_by(Ref.updated_at.desc()).offset(skip).limit(limit).all()

    # 그룹 경로를 포함한 응답 생성
    result = []
    for ref in refs:
        ref_dict = {
            "id": ref.id,
            "title": ref.title,
            "summary": ref.summary,
            "user_id": ref.user_id,
            "group_id": ref.group_id,
            "group_name": get_group_path(db, ref.group_id) if ref.group_id else None,
            "created_at": ref.created_at,
            "updated_at": ref.updated_at,
            "hashtags": ref.hashtags,
        }
        result.append(ref_dict)

    return result


@router.get("/{ref_id}", response_model=RefResponse)
def get_ref(
        ref_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """특정 레퍼런스 조회 (그룹 경로 포함)"""
    ref = db.query(Ref).options(
        joinedload(Ref.group),
        joinedload(Ref.hashtags)
    ).filter(
        Ref.id == ref_id,
        Ref.user_id == current_user.id,
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
        db: Session = Depends(get_db),
):
    """레퍼런스 수정"""
    ref = db.query(Ref).filter(
        Ref.id == ref_id,
        Ref.user_id == current_user.id,
    ).first()
    if not ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ref not found"
        )

    # 그룹 변경
    if ref_data.group_id is not None:
        if ref_data.group_id != 0:
            group = db.query(Group).filter(
                Group.id == ref_data.group_id,
                Group.user_id == current_user.id,
            ).first()
            if not group:
                raise HTTPException(status_code=404, detail="Group not found")
        ref.group_id = ref_data.group_id if ref_data.group_id != 0 else None

    # 해시태그 업데이트
    if ref_data.hashtags is not None:
        ref.hashtags.clear()
        for tag_name in ref_data.hashtags:
            hashtag = get_or_create_hashtag(db, tag_name)
            ref.hashtags.append(hashtag)

    # 기타 필드 업데이트
    if ref_data.title is not None:
        ref.title = ref_data.title
    if ref_data.summary is not None:
        ref.summary = ref_data.summary
    if ref_data.content is not None:
        ref.content = ref_data.content

    db.commit()
    db.refresh(ref)
    return ref


@router.delete("/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ref(
        ref_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """레퍼런스 삭제"""
    ref = db.query(Ref).filter(
        Ref.id == ref_id,
        Ref.user_id == current_user.id,
    ).first()
    if not ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ref not found"
        )
    db.delete(ref)
    db.commit()
    return None
