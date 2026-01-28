from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User, Group, Ref
from app.schemas import GroupCreate, GroupUpdate, GroupResponse, GroupWithRefCount
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/", response_model=GroupResponse, status_code=201)
def create_group(
        group_data: GroupCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    새 그룹 생성
    """

    # 부모 그룹 확인
    if group_data.parent_id:
        parent_group = db.query(Group).filter(
            Group.id == group_data.parent_id,
            Group.user_id == current_user.id
        ).first()

        if not parent_group:
            raise HTTPException(status_code=404, detail="Parent group not found")

    # 같은 부모 아래 같은 이름의 그룹이 있는지 확인
    existing_group = db.query(Group).filter(
        Group.user_id == current_user.id,
        Group.name == group_data.name,
        Group.parent_id == group_data.parent_id
    ).first()

    if existing_group:
        raise HTTPException(status_code=400, detail="Group with this name already exists in this parent")

    new_group = Group(
        name=group_data.name,
        description=group_data.description,
        user_id=current_user.id,
        parent_id=group_data.parent_id
    )

    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    return new_group


@router.get("/", response_model=list[GroupWithRefCount])
def get_groups(
        parent_id: Optional[int] = None,
        include_nested: bool = False,  # 이미 구현되어 있음
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    현재 사용자의 모든 그룹 조회 (논문 개수 포함)
    - parent_id가 None이면 루트 그룹들만 반환
    - parent_id가 지정되면 해당 그룹의 자식 그룹들 반환
    - include_nested=True면 모든 그룹을 계층 구조 없이 반환
    """
    if include_nested:
        # 모든 그룹 반환
        groups = db.query(Group).filter(Group.user_id == current_user.id).order_by(Group.name).all()
    else:
        # 특정 레벨의 그룹만 반환
        groups = db.query(Group).filter(
            Group.user_id == current_user.id,
            Group.parent_id == parent_id
        ).order_by(Group.name).all()

    result = []
    for group in groups:
        result.append({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "parent_id": group.parent_id,
            "ref_count": len(group.refs),
            "children_count": len(group.children),
            "created_at": group.created_at,
            "updated_at": group.updated_at
        })

    return result


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
        group_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    특정 그룹 조회
    """
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return group


@router.get("/tree")
def get_groups_tree(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    계층 구조로 그룹 트리 반환
    """

    def build_tree(parent_id: Optional[int] = None):
        groups = db.query(Group).filter(
            Group.user_id == current_user.id,
            Group.parent_id == parent_id
        ).order_by(Group.name).all()

        tree = []
        for group in groups:
            tree.append({
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "parent_id": group.parent_id,
                "ref_count": len(group.refs),
                "children_count": len(group.children),
                "created_at": group.created_at.isoformat(),
                "updated_at": group.updated_at.isoformat(),
                "children": build_tree(group.id)  # 재귀적으로 자식 그룹 가져오기
            })
        return tree

    return build_tree()


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
        group_id: int,
        group_data: GroupUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    그룹 정보 수정
    """
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

        # 부모 그룹 변경 시 순환 참조 방지
    if group_data.parent_id is not None:
        if group_data.parent_id == group_id:
            raise HTTPException(status_code=400, detail="A group cannot be its own parent")

        # 자신의 자손을 부모로 설정하려는지 확인
        if group_data.parent_id:
            parent = db.query(Group).filter(Group.id == group_data.parent_id).first()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent group not found")

            # 부모의 조상 체크
            current = parent
            while current:
                if current.id == group_id:
                    raise HTTPException(status_code=400, detail="Cannot set a descendant as parent")
                current = db.query(Group).filter(Group.id == current.parent_id).first() if current.parent_id else None

        # 이름 중복 체크
    if group_data.name and group_data.name != group.name:
        existing_group = db.query(Group).filter(
            Group.user_id == current_user.id,
            Group.name == group_data.name,
            Group.parent_id == (group_data.parent_id if group_data.parent_id is not None else group.parent_id)
        ).first()

        if existing_group:
            raise HTTPException(status_code=400, detail="Group with this name already exists in this parent")

        # 업데이트
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
        db: Session = Depends(get_db)
):
    """
    그룹의 전체 경로 반환 (breadcrumb용)
    예: [{"id": 1, "name": "Research"}, {"id": 2, "name": "ML"}, {"id": 3, "name": "Papers"}]
    """
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    path = []
    current = group

    # 루트까지 올라가면서 경로 구성
    while current:
        path.insert(0, {
            "id": current.id,
            "name": current.name
        })
        if current.parent_id:
            current = db.query(Group).filter(Group.id == current.parent_id).first()
        else:
            current = None

    return path


@router.delete("/{group_id}", status_code=204)
def delete_group(
        group_id: int,
        delete_refs: bool = Query(False,
                                  description="If true, delete all refs in this group. If false, set refs to ungrouped."),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    그룹 삭제

    Parameters:
    - group_id: 삭제할 그룹 ID
    - delete_refs: True이면 그룹 내 레퍼런스도 삭제, False이면 ungrouped로 변경
    """
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # 레퍼런스 처리
    if delete_refs:
        # 그룹 내 모든 레퍼런스 삭제
        db.query(Ref).filter(Ref.group_id == group_id).delete(synchronize_session=False)
    else:
        # 그룹 내 레퍼런스를 ungrouped로 변경 (group_id를 NULL로)
        db.query(Ref).filter(Ref.group_id == group_id).update(
            {"group_id": None}, synchronize_session=False
        )

    # 그룹 삭제 (CASCADE로 하위 그룹도 자동 삭제됨)
    db.delete(group)
    db.commit()
    return None