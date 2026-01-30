from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

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


def count_total_refs_in_tree(db: Session, group_id: int) -> int:
    """
    그룹과 모든 하위 그룹의 레퍼런스 총 개수 계산

    Args:
        db: 데이터베이스 세션
        group_id: 그룹 ID

    Returns:
        int: 전체 레퍼런스 개수
    """
    # 현재 그룹의 레퍼런스 개수
    total_refs = db.query(Ref).filter(Ref.group_id == group_id).count()

    # 자식 그룹들의 레퍼런스 개수를 재귀적으로 더함
    children = db.query(Group).filter(Group.parent_id == group_id).all()
    for child in children:
        total_refs += count_total_refs_in_tree(db, child.id)

    return total_refs


@router.get("/{group_id}/ref-count")
def get_group_ref_count(
        group_id: int,
        include_subgroups: bool = Query(True, description="Include references in all subgroups"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    그룹의 레퍼런스 개수 조회 (서브그룹 포함 가능)

    Parameters:
    - group_id: 그룹 ID
    - include_subgroups: True이면 모든 하위 그룹의 레퍼런스도 포함

    Returns:
    - ref_count: 레퍼런스 개수
    - has_subgroups: 하위 그룹 존재 여부
    """
    # 그룹 존재 및 권한 확인
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if include_subgroups:
        # 모든 하위 그룹 포함
        ref_count = count_total_refs_in_tree(db, group_id)
    else:
        # 현재 그룹만
        ref_count = db.query(Ref).filter(Ref.group_id == group_id).count()

    # 하위 그룹 존재 여부
    has_subgroups = db.query(Group).filter(Group.parent_id == group_id).count() > 0

    return {
        "ref_count": ref_count,
        "has_subgroups": has_subgroups,
        "group_id": group_id,
        "group_name": group.name,
    }


def get_all_descendant_group_ids(db: Session, group_id: int) -> List[int]:
    """
    재귀적으로 모든 하위 그룹의 ID를 수집
    """
    group_ids = [group_id]
    children = db.query(Group).filter(Group.parent_id == group_id).all()
    for child in children:
        group_ids.extend(get_all_descendant_group_ids(db, child.id))
    return group_ids


def delete_group_tree(db: Session, group_id: int, delete_refs: bool) -> int:
    """
    그룹과 모든 하위 그룹을 재귀적으로 삭제 (깊이 우선 탐색)
    """
    deleted_count = 0

    # 먼저 자식 그룹들을 재귀적으로 삭제 (깊이 우선)
    children = db.query(Group).filter(Group.parent_id == group_id).all()
    for child in children:
        deleted_count += delete_group_tree(db, child.id, delete_refs)

    # 현재 그룹의 레퍼런스 처리
    if delete_refs:
        refs_deleted = db.query(Ref).filter(Ref.group_id == group_id).delete(synchronize_session=False)
        if refs_deleted > 0:
            print(f"  Deleted {refs_deleted} refs from group {group_id}")
    else:
        refs_moved = db.query(Ref).filter(Ref.group_id == group_id).update(
            {"group_id": None},
            synchronize_session=False
        )
        if refs_moved > 0:
            print(f"  Moved {refs_moved} refs to ungrouped from group {group_id}")

    # 현재 그룹 삭제
    group = db.query(Group).filter(Group.id == group_id).first()
    if group:
        db.delete(group)
        deleted_count += 1
        print(f"  Deleted group {group_id} ({group.name})")

    return deleted_count


@router.delete("/{group_id}", status_code=204)
def delete_group(
        group_id: int,
        delete_refs: bool = Query(
            False,
            description="If true, delete all refs in this group and subgroups. If false, set all refs to ungrouped."
        ),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    그룹 삭제 (모든 하위 그룹과 레퍼런스 포함)
    """
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    print(f"\n=== Deleting group '{group.name}' (ID: {group_id}) ===")
    print(f"Delete refs: {delete_refs}")

    # 재귀적으로 그룹 트리 삭제 (하위 그룹부터 삭제)
    deleted_count = delete_group_tree(db, group_id, delete_refs)

    # 변경사항 커밋
    db.commit()

    print(f"=== Deleted {deleted_count} group(s) successfully ===\n")

    return None