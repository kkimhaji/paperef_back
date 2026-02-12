from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from app.database import engine, Base
from app.routers import auth, refs, groups, hashtags

load_dotenv()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Paperef API",
    description="논문 메모 관리 API",
    version="1.0.0"
)


# 환경에 따른 CORS 설정
ENV = os.getenv("ENV", "development")

if ENV == "production":
    # 프로덕션: 특정 도메인만 허용
    origins = [
        "https://paperef.com",
        "https://www.paperef.com",
    ]
else:
    # 개발: 로컬 개발 환경 허용
    origins = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
    ],
    expose_headers=["Content-Length", "Content-Range"],
    max_age=3600,  # Preflight 요청 캐시 시간 (1시간)
)

# 라우터 등록
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(refs.router, prefix="/refs", tags=["Refs"])
app.include_router(groups.router, prefix="/groups", tags=["Groups"])
app.include_router(hashtags.router, prefix="/hashtags", tags=["Hashtags"])

@app.get("/")
def root():
    return {"message": "Welcome to Paperef API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
