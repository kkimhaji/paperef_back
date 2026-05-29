from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from app.database import engine, Base, SessionLocal
from app.routers import auth, refs, groups, hashtags
from app.token_cleanup import cleanup_tokens

load_dotenv()

ENV = os.getenv("ENV", "development")

if ENV == "production":
    ALLOWED_ORIGINS = [
        "https://paperef.com",
        "https://www.paperef.com",
        "https://d29n3vqbryd7hd.cloudfront.net",
    ]
else:
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
    ]


async def _periodic_token_cleanup() -> None:
    """Runs every 24 hours in non-production environments to purge expired tokens."""
    while True:
        await asyncio.sleep(60 * 60 * 24)
        db = SessionLocal()
        try:
            cleanup_tokens(db)
        except Exception as e:
            print(f"[TokenCleanup] Error: {e}")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    cleanup_task = None
    if ENV != "production":
        cleanup_task = asyncio.create_task(_periodic_token_cleanup())
        print("[TokenCleanup] Periodic cleanup task started (every 24h)")

    yield

    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        print("[TokenCleanup] Periodic cleanup task stopped")


app = FastAPI(
    title="Paperef API",
    description="API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
    max_age=3600,
)

app.include_router(auth.router,     prefix="/auth",     tags=["Authentication"])
app.include_router(refs.router,     prefix="/refs",     tags=["Refs"])
app.include_router(groups.router,   prefix="/groups",   tags=["Groups"])
app.include_router(hashtags.router, prefix="/hashtags", tags=["Hashtags"])


@app.get("/")
def root():
    return {"message": "Welcome to Paperef API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}