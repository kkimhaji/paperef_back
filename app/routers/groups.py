from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User, Group
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
    # 같은 이름의 그룹이 이미 있는지 확인
    existing_group = db.query(Group).filter(
        Group.user_id == current_user.id,
        Group.name == group_data.name
    ).first()

    if existing_group:
        raise HTTPException(status_code=400, detail="Group with this name already exists")

    new_group = Group(
        name=group_data.name,
        description=group_data.description,
        user_id=current_user.id
    )

    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    return new_group


@router.get("/", response_model=list[GroupWithRefCount])
def get_groups(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    현재 사용자의 모든 그룹 조회 (논문 개수 포함)
    """
    groups = db.query(Group).filter(Group.user_id == current_user.id).order_by(Group.name).all()

    result = []
    for group in groups:
        result.append({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "ref_count": len(group.refs),
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

    # 이름 중복 체크
    if group_data.name and group_data.name != group.name:
        existing_group = db.query(Group).filter(
            Group.user_id == current_user.id,
            Group.name == group_data.name
        ).first()

        if existing_group:
            raise HTTPException(status_code=400, detail="Group with this name already exists")

    # 업데이트
    if group_data.name is not None:
        group.name = group_data.name
    if group_data.description is not None:
        group.description = group_data.description

    db.commit()
    db.refresh(group)

    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(
        group_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    그룹 삭제 (그룹 내 논문들의 group_id는 NULL로 설정됨)
    """
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.user_id == current_user.id
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    db.delete(group)
    db.commit()

    return None
