from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=128)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Token Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
    token_type: Optional[str] = "access"


# Group Schemas
class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class GroupCreate(GroupBase):
    parent_id: Optional[int] = None

class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None

class GroupResponse(GroupBase):
    id: int
    user_id: int
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupWithRefCount(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    ref_count: int
    children_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Hashtag Schemas
class HashtagBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class HashtagResponse(HashtagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# Ref Schemas
class RefBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    summary: Optional[str] = None
    content: Optional[str] = None


class RefCreate(RefBase):
    group_id: Optional[int] = None
    hashtags: Optional[list[str]] = []


class RefUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[str] = None
    content: Optional[str] = None
    group_id: Optional[int] = None
    hashtags: Optional[list[str]] = None


class RefResponse(RefBase):
    id: int
    user_id: int
    group_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    hashtags: list[HashtagResponse] = []

    model_config = ConfigDict(from_attributes=True)


class RefListResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    user_id: int
    group_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    hashtags: list[HashtagResponse] = []

    model_config = ConfigDict(from_attributes=True)
