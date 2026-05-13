from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import sys
from pathlib import Path

from app.config import settings
from app.database import engine, Base
from app.courses import router as courses_router
from app.settings_api import router as settings_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bloom Learning API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses_router)
app.include_router(settings_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve frontend static files if they exist (must be last — catch-all mount)
def _frontend_dist_path() -> str | None:
    candidates = []
    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.append(bundle_dir / "frontend" / "dist")
        candidates.append(Path(sys.executable).parent / "frontend" / "dist")

    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


frontend_dist = _frontend_dist_path()
if frontend_dist:
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
