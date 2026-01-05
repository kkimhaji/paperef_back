from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# 논문과 해시태그의 다대다 관계 테이블
paper_hashtags = Table(
    'paper_hashtags',
    Base.metadata,
    Column('paper_id', Integer, ForeignKey('papers.id', ondelete='CASCADE')),
    Column('hashtag_id', Integer, ForeignKey('hashtags.id', ondelete='CASCADE'))
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    papers = relationship("Paper", back_populates="owner", cascade="all, delete-orphan")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    summary = Column(Text)  # 카드뷰에 표시될 간단한 메모
    content = Column(Text)  # 상세 페이지에 표시될 본문
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="papers")
    hashtags = relationship(
        "Hashtag",
        secondary=paper_hashtags,
        back_populates="papers"
    )


class Hashtag(Base):
    __tablename__ = "hashtags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)

    papers = relationship(
        "Paper",
        secondary=paper_hashtags,
        back_populates="hashtags"
    )