import base64
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import exists
from typing import Optional, List

from app.database import get_db
from app.models import User, Ref, RefSummary, Hashtag, Group
from app.schemas import RefCreate, RefUpdate, RefResponse, RefCursorPageResponse
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


def _apply_summaries(ref: Ref, summaries: list[str]) -> None:
    """Replace all RefSummary rows for the given Ref."""
    ref.ref_summaries.clear()
    for position, content in enumerate(summaries):
        ref.ref_summaries.append(RefSummary(content=content, position=position))


def _load_ref_options():
    return [
        joinedload(Ref.group),
        joinedload(Ref.hashtags),
        joinedload(Ref.ref_summaries),
    ]


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

    if ref_data.hashtags:
        for tag_name in ref_data.hashtags:
            new_ref.hashtags.append(get_or_create_hashtag(db, tag_name))

    db.add(new_ref)
    db.commit()
    db.refresh(new_ref)

    # Re-load with all relationships for response serialization
    return db.query(Ref).options(*_load_ref_options()).filter(Ref.id == new_ref.id).first()


@router.get("/", response_model=RefCursorPageResponse)
def get_refs(
    limit:   int           = Query(20, ge=1, le=50),
    cursor:  Optional[str] = Query(None, description="Pagination cursor"),
    hashtag: Optional[str] = Query(None),
    group_id: Optional[int] = Query(None),
    search:  Optional[str] = Query(None),
    include_subgroups: bool = Query(True),
    current_user: User     = Depends(get_current_user),
    db: Session            = Depends(get_db),
):
    base_query = (
        db.query(Ref)
        .options(*_load_ref_options())
        .filter(Ref.user_id == current_user.id)
    )

    # 기존 필터 적용
    if group_id is not None:
        if group_id == 0:
            base_query = base_query.filter(Ref.group_id == None)
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
                (RefSummary.ref_id == Ref.id)
                & RefSummary.content.ilike(pattern)
            )
        )

    # Cursor 디코딩 및 적용
    if cursor:
        cursor_data = _decode_cursor(cursor)
        if cursor_data:
            cursor_updated_at = cursor_data["updated_at"]
            cursor_id         = cursor_data["id"]
            base_query = base_query.filter(
                (Ref.updated_at < cursor_updated_at)
                | (
                    (Ref.updated_at == cursor_updated_at)
                    & (Ref.id < cursor_id)
                )
            )

    refs = (
        base_query
        .order_by(Ref.updated_at.desc(), Ref.id.desc())
        .limit(limit + 1)   # 1개 더 가져와서 has_more 판단
        .all()
    )

    has_more   = len(refs) > limit
    items      = refs[:limit]           # 실제 반환할 항목
    next_cursor = None

    if has_more and items:
        last       = items[-1]
        next_cursor = _encode_cursor(last.updated_at, last.id)

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


def _encode_cursor(updated_at: datetime, ref_id: int) -> str:
    data = {"updated_at": updated_at.isoformat(), "id": ref_id}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def _decode_cursor(cursor: str) -> Optional[dict]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return {
            "updated_at": datetime.fromisoformat(data["updated_at"]),
            "id":         data["id"],
        }
    except Exception:
        return None

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
        Ref.id == ref_id,
        Ref.user_id == current_user.id,
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
        Ref.id == ref_id,
        Ref.user_id == current_user.id,
    ).first()
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ref not found")
    db.delete(ref)
    db.commit()
