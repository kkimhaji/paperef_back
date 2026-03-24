from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/paperef_db"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=5,         # 기본 유지 연결 수
    max_overflow=10,     # 최대 추가 연결 수 (최대 동시 연결: 15)
    pool_timeout=30,     # 연결 대기 최대 30초
    pool_recycle=1800,   # 30분마다 연결 교체 (유휴 연결 끊김 방지)
    pool_pre_ping=True,  # 사용 전 연결 유효성 확인
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()