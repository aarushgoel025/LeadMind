import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from database import engine, Base
import models  # noqa: F401 — registers all ORM models
from routers import auth, repos, scan as scan_router

load_dotenv()

# Create tables on startup (idempotent — skips existing tables)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LeadMind API",
    description="AI-powered security and code quality audit for tech leads.",
    version="1.0.0",
)

# ── Session middleware (server-side, httpOnly cookie) ──────────────────────────
IS_PROD = os.getenv("ENV") == "production"
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change_me_in_production_extremely_secure_key"),
    session_cookie="leadmind_session",
    max_age=60 * 60 * 24,   # 24 hours
    same_site="lax",
    https_only=IS_PROD,      # set True in production (behind HTTPS)
)

# ── CORS (allow frontend dev server) ──────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,  # Required for session cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(repos.router)
app.include_router(scan_router.router)


@app.get("/")
def root():
    return {
        "service": "LeadMind API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
