from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List

from app.database import get_db
from app.models import User, Group, Ref
from app.schemas import GroupCreate, GroupUpdate, GroupResponse, GroupWithRefCount
from app.dependencies import get_current_user

router = APIRouter(redirect_slashes=False)

def get_all_descendant_group_ids(db: Session, group_id: int) -> List[int]:
    """
    WITH RECURSIVE로 모든 하위 그룹 ID를 단일 쿼리로 수집.
    기존 재귀 Python 함수 대비 N+1 쿼리 문제 해결.
    """
    result = db.execute(
        text("""
            WITH RECURSIVE descendants AS (
                SELECT id FROM groups WHERE id = :group_id
                UNION ALL
                SELECT g.id FROM groups g
                INNER JOIN descendants d ON g.parent_id = d.id
            )
            SELECT id FROM descendants
        """),
        {"group_id": group_id},
    )
    return [row[0] for row in result]


def count_total_refs_in_tree(db: Session, group_id: int) -> int:
    """
    WITH RECURSIVE로 그룹 트리 전체의 레퍼런스 수를 단일 쿼리로 집계.
    """
    result = db.execute(
        text("""
            WITH RECURSIVE descendants AS (
                SELECT id FROM groups WHERE id = :group_id
                UNION ALL
                SELECT g.id FROM groups g
                INNER JOIN descendants d ON g.parent_id = d.id
            )
            SELECT COUNT(*) FROM refs
            WHERE group_id IN (SELECT id FROM descendants)
        """),
        {"group_id": group_id},
    )
    return result.scalar() or 0


def _get_descendant_ids_excluding_root(db: Session, group_id: int) -> List[int]:
    """루트를 제외한 하위 그룹 ID 목록 (삭제 시 사용)."""
    result = db.execute(
        text("""
            WITH RECURSIVE descendants AS (
                SELECT id FROM groups WHERE parent_id = :group_id
                UNION ALL
                SELECT g.id FROM groups g
                INNER JOIN descendants d ON g.parent_id = d.id
            )
            SELECT id FROM descendants
        """),
        {"group_id": group_id},
    )
    return [row[0] for row in result]


@router.post("/", response_model=GroupResponse, status_code=201)
def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if group_data.parent_id:
        parent = db.query(Group).filter(
            Group.id == group_data.parent_id,
            Group.user_id == current_user.id,
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent group not found")

    existing = db.query(Group).filter(
        Group.user_id == current_user.id,
        Group.name == group_data.name,
        Group.parent_id == group_data.parent_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Group with this name already exists in this parent",
        )

    new_group = Group(
        name=group_data.name,
        description=group_data.description,
        user_id=current_user.id,
        parent_id=group_data.parent_id,
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group


@router.get("/", response_model=list[GroupWithRefCount])
def get_groups(
    parent_id: Optional[int] = None,
    include_nested: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if include_nested:
        groups = db.query(Group).filter(
            Group.user_id == current_user.id
        ).order_by(Group.name).all()
    else:
        groups = db.query(Group).filter(
            Group.user_id == current_user.id,
            Group.parent_id == parent_id,
        ).order_by(Group.name).all()

    return [
        {
            "id":             group.id,
            "name":           group.name,
            "description":    group.description,
            "parent_id":      group.parent_id,
            "ref_count":      len(group.refs),
            "children_count": len(group.children),
            "created_at":     group.created_at,
            "updated_at":     group.updated_at,
        }
        for group in groups
    ]


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.get("/tree")
def get_groups_tree(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def build_tree(parent_id: Optional[int] = None):
        groups = db.query(Group).filter(
            Group.user_id == current_user.id,
            Group.parent_id == parent_id,
        ).order_by(Group.name).all()

        return [
            {
                "id":             g.id,
                "name":           g.name,
                "description":    g.description,
                "parent_id":      g.parent_id,
                "ref_count":      len(g.refs),
                "children_count": len(g.children),
                "created_at":     g.created_at.isoformat(),
                "updated_at":     g.updated_at.isoformat(),
                "children":       build_tree(g.id),
            }
            for g in groups
        ]

    return build_tree()


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    group_data: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group_data.parent_id is not None:
        if group_data.parent_id == group_id:
            raise HTTPException(
                status_code=400, detail="A group cannot be its own parent"
            )
        if group_data.parent_id:
            parent = db.query(Group).filter(
                Group.id == group_data.parent_id
            ).first()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent group not found")

            # 자신의 자손을 부모로 설정하는 순환 참조 방지
            # WITH RECURSIVE로 단일 쿼리 확인
            descendant_ids = get_all_descendant_group_ids(db, group_id)
            if group_data.parent_id in descendant_ids:
                raise HTTPException(
                    status_code=400, detail="Cannot set a descendant as parent"
                )

    if group_data.name and group_data.name != group.name:
        target_parent = (
            group_data.parent_id
            if group_data.parent_id is not None
            else group.parent_id
        )
        existing = db.query(Group).filter(
            Group.user_id == current_user.id,
            Group.name == group_data.name,
            Group.parent_id == target_parent,
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Group with this name already exists in this parent",
            )

    if group_data.name is not None:
        group.name = group_data.name
    if group_data.description is not None:
        group.description = group_data.description
    if group_data.parent_id is not None:
        group.parent_id = group_data.parent_id if group_data.parent_id > 0 else None

    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}/path")
def get_group_path(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    path = []
    current = group
    while current:
        path.insert(0, {"id": current.id, "name": current.name})
        current = (
            db.query(Group).filter(Group.id == current.parent_id).first()
            if current.parent_id else None
        )
    return path


@router.get("/{group_id}/ref-count")
def get_group_ref_count(
    group_id: int,
    include_subgroups: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if include_subgroups:
        ref_count = count_total_refs_in_tree(db, group_id)  # 단일 쿼리
    else:
        ref_count = db.query(Ref).filter(Ref.group_id == group_id).count()

    has_subgroups = db.query(Group).filter(Group.parent_id == group_id).count() > 0

    return {
        "ref_count":    ref_count,
        "has_subgroups": has_subgroups,
        "group_id":     group_id,
        "group_name":   group.name,
    }


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    delete_refs: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # WITH RECURSIVE로 모든 하위 그룹 ID 단일 쿼리 수집
    all_ids = get_all_descendant_group_ids(db, group_id)  # 루트 포함

    if delete_refs:
        # 해당 그룹 트리의 레퍼런스 일괄 삭제
        db.query(Ref).filter(Ref.group_id.in_(all_ids)).delete(
            synchronize_session=False
        )
    else:
        # 레퍼런스를 ungrouped로 이동
        db.query(Ref).filter(Ref.group_id.in_(all_ids)).update(
            {"group_id": None}, synchronize_session=False
        )

    # 하위 그룹 → 루트 순서로 삭제 (FK 제약 준수)
    # parent_id가 있는 것부터 삭제하면 FK 위반 없음
    db.query(Group).filter(Group.id.in_(all_ids)).delete(
        synchronize_session=False
    )
    db.commit()
    return None