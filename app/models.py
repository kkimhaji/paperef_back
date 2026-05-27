from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


ref_hashtags = Table(
    "ref_hashtags",
    Base.metadata,
    Column("ref_id", Integer, ForeignKey("refs.id", ondelete="CASCADE")),
    Column("hashtag_id", Integer, ForeignKey("hashtags.id", ondelete="CASCADE")),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(128), index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    refs = relationship("Ref", back_populates="owner", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="owner", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="owner", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)

    owner = relationship("User", back_populates="refresh_tokens")


class RefSummary(Base):
    __tablename__ = "ref_summaries"

    id = Column(Integer, primary_key=True, index=True)
    ref_id = Column(Integer, ForeignKey("refs.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    position = Column(Integer, nullable=False, default=0)

    ref = relationship("Ref", back_populates="ref_summaries")


class Ref(Base):
    __tablename__ = "refs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    content = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="refs")
    group = relationship("Group", back_populates="refs")
    hashtags = relationship(
        "Hashtag",
        secondary=ref_hashtags,
        back_populates="refs",
    )
    ref_summaries = relationship(
        "RefSummary",
        back_populates="ref",
        cascade="all, delete-orphan",
        order_by="RefSummary.position",
    )

    @property
    def group_name(self) -> str | None:
        return self.group.name if self.group else None

    @property
    def summaries(self) -> list[str]:
        return [s.content for s in self.ref_summaries]


class Hashtag(Base):
    __tablename__ = "hashtags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)

    refs = relationship("Ref", secondary=ref_hashtags, back_populates="hashtags")


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="groups")
    refs = relationship("Ref", back_populates="group")
    parent = relationship("Group", remote_side=[id], backref="children")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def is_valid(self) -> bool:
        return not self.used and datetime.utcnow() < self.expires_at