import base64
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import exists, asc, desc
from typing import Optional, List

from app.database import get_db
from app.models import User, Ref, RefSummary, Hashtag, Group
from app.schemas import RefCreate, RefUpdate, RefResponse, RefCursorPageResponse, RefSortBy
from app.dependencies import get_current_user
from app.routers.groups import get_all_descendant_group_ids

router = APIRouter(redirect_slashes=False)


def get_or_create_hashtag(db: Session, name: str) -> Hashtag:
    name = name.strip().lower()
    hashtag = db.query(Hashtag).filter(Hashtag.name == name).first()
    if not hashtag:
        hashtag = Hashtag(name=name)
        db.add(hashtag)
        db.commit()
        db.refresh(hashtag)
    return hashtag


def get_group_path(db: Session, group_id: int) -> str:
    parts: list[str] = []
    current = db.query(Group).filter(Group.id == group_id).first()
    while current:
        parts.insert(0, current.name)
        current = (
            db.query(Group).filter(Group.id == current.parent_id).first()
            if current.parent_id else None
        )
    return " / ".join(parts)


def _load_ref_options():
    return [
        joinedload(Ref.group),
        joinedload(Ref.hashtags),
        joinedload(Ref.ref_summaries),
    ]


def _apply_summaries(ref: Ref, summaries: list[str]) -> None:
    ref.ref_summaries.clear()
    for position, content in enumerate(summaries):
        ref.ref_summaries.append(RefSummary(content=content, position=position))


def _encode_cursor(sort_by: RefSortBy, ref: Ref) -> str:
    """정렬 방식에 따라 커서에 다른 기준 컬럼값을 인코딩."""
    sort_value = (
        ref.updated_at.isoformat()
        if sort_by == RefSortBy.UPDATED_DESC
        else ref.created_at.isoformat()
    )
    data = {
        "sort_by":    sort_by.value,
        "sort_value": sort_value,
        "id":         ref.id,
    }
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def _decode_cursor(cursor: str) -> Optional[dict]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return {
            "sort_by":    data["sort_by"],
            "sort_value": datetime.fromisoformat(data["sort_value"]),
            "id":         data["id"],
        }
    except Exception:
        return None


def _apply_cursor_filter(query, cursor_data: dict, sort_by: RefSortBy):
    """커서 이후 항목만 반환하도록 WHERE 조건 추가."""
    sort_value = cursor_data["sort_value"]
    cursor_id  = cursor_data["id"]

    sort_col = (
        Ref.updated_at
        if sort_by == RefSortBy.UPDATED_DESC
        else Ref.created_at
    )

    if sort_by == RefSortBy.CREATED_ASC:
        # 오름차순: sort_value보다 크거나, 같으면 id가 큰 것
        return query.filter(
            (sort_col > sort_value)
            | ((sort_col == sort_value) & (Ref.id > cursor_id))
        )
    else:
        # 내림차순: sort_value보다 작거나, 같으면 id가 작은 것
        return query.filter(
            (sort_col < sort_value)
            | ((sort_col == sort_value) & (Ref.id < cursor_id))
        )


def _apply_ordering(query, sort_by: RefSortBy):
    """정렬 방식에 따른 ORDER BY 적용."""
    if sort_by == RefSortBy.UPDATED_DESC:
        return query.order_by(desc(Ref.updated_at), desc(Ref.id))
    elif sort_by == RefSortBy.CREATED_DESC:
        return query.order_by(desc(Ref.created_at), desc(Ref.id))
    else:  # CREATED_ASC
        return query.order_by(asc(Ref.created_at), asc(Ref.id))


@router.post("/", response_model=RefResponse, status_code=status.HTTP_201_CREATED)
def create_ref(
    ref_data: RefCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if ref_data.group_id:
        group = db.query(Group).filter(
            Group.id == ref_data.group_id,
            Group.user_id == current_user.id,
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

    new_ref = Ref(
        title=ref_data.title,
        content=ref_data.content,
        user_id=current_user.id,
        group_id=ref_data.group_id,
    )
    _apply_summaries(new_ref, ref_data.summaries)

    for tag_name in ref_data.hashtags:
        new_ref.hashtags.append(get_or_create_hashtag(db, tag_name))

    db.add(new_ref)
    db.commit()
    db.refresh(new_ref)
    return db.query(Ref).options(*_load_ref_options()).filter(Ref.id == new_ref.id).first()


@router.get("/", response_model=RefCursorPageResponse)
def get_refs(
    limit:             int          = Query(20, ge=1, le=50),
    cursor:            Optional[str] = Query(None),
    sort_by:           RefSortBy    = Query(RefSortBy.UPDATED_DESC),
    hashtag:           Optional[str] = Query(None),
    group_id:          Optional[int] = Query(None),
    search:            Optional[str] = Query(None),
    include_subgroups: bool          = Query(True),
    current_user:      User          = Depends(get_current_user),
    db:                Session       = Depends(get_db),
):
    base_query = (
        db.query(Ref)
        .options(*_load_ref_options())
        .filter(Ref.user_id == current_user.id)
    )

    # 필터 적용
    if group_id is not None:
        if group_id == 0:
            base_query = base_query.filter(Ref.group_id == None)  # noqa
        elif include_subgroups:
            base_query = base_query.filter(
                Ref.group_id.in_(get_all_descendant_group_ids(db, group_id))
            )
        else:
            base_query = base_query.filter(Ref.group_id == group_id)

    if hashtag:
        base_query = base_query.join(Ref.hashtags).filter(
            Hashtag.name == hashtag.strip().lower()
        )

    if search:
        pattern = f"%{search}%"
        base_query = base_query.filter(
            (Ref.title.ilike(pattern))
            | (Ref.content.ilike(pattern))
            | exists().where(
                (RefSummary.ref_id == Ref.id) & RefSummary.content.ilike(pattern)
            )
        )

    # 커서 적용 — 커서의 sort_by와 요청의 sort_by가 다르면 커서 무시
    if cursor:
        cursor_data = _decode_cursor(cursor)
        if cursor_data and cursor_data["sort_by"] == sort_by.value:
            base_query = _apply_cursor_filter(base_query, cursor_data, sort_by)

    base_query = _apply_ordering(base_query, sort_by)

    refs     = base_query.limit(limit + 1).all()
    has_more = len(refs) > limit
    items    = refs[:limit]

    next_cursor = _encode_cursor(sort_by, items[-1]) if has_more and items else None

    return {
        "items": [
            {
                "id":         ref.id,
                "title":      ref.title,
                "summaries":  [s.content for s in ref.ref_summaries],
                "user_id":    ref.user_id,
                "group_id":   ref.group_id,
                "group_name": get_group_path(db, ref.group_id) if ref.group_id else None,
                "created_at": ref.created_at,
                "updated_at": ref.updated_at,
                "hashtags":   ref.hashtags,
            }
            for ref in items
        ],
        "next_cursor": next_cursor,
        "has_more":    has_more,
    }


@router.get("/{ref_id}", response_model=RefResponse)
def get_ref(
    ref_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ref = (
        db.query(Ref)
        .options(*_load_ref_options())
        .filter(Ref.id == ref_id, Ref.user_id == current_user.id)
        .first()
    )
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ref not found")
    return ref


@router.put("/{ref_id}", response_model=RefResponse)
def update_ref(
    ref_id: int,
    ref_data: RefUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ref = db.query(Ref).options(joinedload(Ref.ref_summaries)).filter(
        Ref.id == ref_id, Ref.user_id == current_user.id,
    ).first()
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ref not found")

    if ref_data.title is not None:
        ref.title = ref_data.title
    if ref_data.content is not None:
        ref.content = ref_data.content
    if ref_data.summaries is not None:
        _apply_summaries(ref, ref_data.summaries)

    if ref_data.group_id is not None:
        if ref_data.group_id == 0:
            ref.group_id = None
        else:
            group = db.query(Group).filter(
                Group.id == ref_data.group_id,
                Group.user_id == current_user.id,
            ).first()
            if not group:
                raise HTTPException(status_code=404, detail="Group not found")
            ref.group_id = ref_data.group_id

    if ref_data.hashtags is not None:
        ref.hashtags.clear()
        for tag_name in ref_data.hashtags:
            ref.hashtags.append(get_or_create_hashtag(db, tag_name))

    db.commit()
    return db.query(Ref).options(*_load_ref_options()).filter(Ref.id == ref.id).first()


@router.delete("/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ref(
    ref_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ref = db.query(Ref).filter(
        Ref.id == ref_id, Ref.user_id == current_user.id,
    ).first()
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ref not found")
    db.delete(ref)
    db.commit()