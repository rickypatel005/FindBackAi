from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import Base, engine

# Ensure models are imported so Base.metadata knows about all tables
from app.models import match, notification, report, user  # noqa: F401

settings = get_settings()

# Initialize DB tables (for SQLite or fresh DB instances)
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)

# Local-disk fallback for uploaded images (app/services/storage.py) used
# when Supabase Storage credentials aren't configured — e.g. local dev or
# a hackathon demo run without a Supabase project provisioned yet. In
# production with Supabase configured, uploads go straight to Supabase
# Storage and this mount simply serves nothing.
_local_storage_dir = Path(settings.LOCAL_STORAGE_DIR)
_local_storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_local_storage_dir)), name="media")


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}
