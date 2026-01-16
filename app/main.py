from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import auth, papers, groups, hashtags

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Paperef API",
    description="논문 메모 관리 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(papers.router, prefix="/papers", tags=["Papers"])
app.include_router(groups.router, prefix="/groups", tags=["Groups"])
app.include_router(hashtags.router, prefix="/hashtags", tags=["Hashtags"])

@app.get("/")
def root():
    return {"message": "Welcome to Paperef API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
