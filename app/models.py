from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# 논문과 해시태그의 다대다 관계 테이블
ref_hashtags = Table(
    'ref_hashtags',
    Base.metadata,
    Column('ref_id', Integer, ForeignKey('refs.id', ondelete='CASCADE')),
    Column('hashtag_id', Integer, ForeignKey('hashtags.id', ondelete='CASCADE'))
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    refs = relationship("Ref", back_populates="owner", cascade="all, delete-orphan")  # 수정
    refresh_tokens = relationship("RefreshToken", back_populates="owner", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="owner", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)

    owner = relationship("User", back_populates="refresh_tokens")


class Ref(Base):
    __tablename__ = "refs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    summary = Column(Text)
    content = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="refs")
    group = relationship("Group", back_populates="refs")
    hashtags = relationship(
        "Hashtag",
        secondary=ref_hashtags,
        back_populates="refs"
    )


class Hashtag(Base):
    __tablename__ = "hashtags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)

    refs = relationship(
        "Ref",
        secondary=ref_hashtags,
        back_populates="hashtags"
    )

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="groups")
    refs = relationship("Ref", back_populates="group")