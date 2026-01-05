from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, papers

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Paper Memo API",
    description="논문 메모 관리 API - 논문 메모 작성, 해시태그 관리, 사용자 인증",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Flutter 웹 개발 서버
        "http://localhost:3000",  # 추가 개발 환경
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(papers.router, prefix="/papers", tags=["Papers"])

@app.get("/")
def root():
    return {
        "message": "Paper Memo API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}