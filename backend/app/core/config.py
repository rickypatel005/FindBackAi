"""
Central configuration for FindBack AI backend.

All values are loaded from environment variables (see .env.example at the
project root). Nothing here should ever be hardcoded secrets — per
Architecture doc Section 9 (Security Architecture) and SRS FR Security
Requirements.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "FindBack AI"
    ENV: str = "development"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # --- Supabase / Database ---
    SUPABASE_URL: str = ""
    NEXT_PUBLIC_SUPABASE_URL: str = ""
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/findback"

    # --- Auth ---
    # "local"    — backend issues + verifies its own JWTs (no Supabase project needed yet)
    # "supabase" — backend delegates sign-up/sign-in to Supabase Auth and
    #              verifies the JWT Supabase issues using SUPABASE_JWT_SECRET
    #              (Project Settings > API > JWT Settings, NOT the anon/service keys)
    AUTH_MODE: str = "local"
    JWT_SECRET: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    SUPABASE_JWT_SECRET: str = ""

    # --- Storage ---
    STORAGE_BUCKET: str = "reports"
    MAX_IMAGE_SIZE_MB: int = 10
    MAX_IMAGES_PER_REPORT: int = 3
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    # Used only when Supabase Storage credentials aren't configured (local
    # dev / hackathon demo without a Supabase project yet) — Phase 3 falls
    # back to serving uploaded images from disk instead of failing outright.
    LOCAL_STORAGE_DIR: str = "./local_storage"
    BACKEND_BASE_URL: str = "http://localhost:8000"

    # --- AI / Models ---
    MODEL_CACHE_DIR: str = "./.model_cache"
    CLIP_MODEL_NAME: str = "ViT-B-32"
    CLIP_PRETRAINED: str = "openai"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    CATEGORY_CONFIDENCE_THRESHOLD: float = 0.35
    # Master switch for the Phase 3 CLIP pipeline. When False (or when
    # open_clip/torch aren't installed / weights can't be fetched),
    # app/services/vision.py transparently falls back to a deterministic,
    # non-ML heuristic so upload/report-creation still work end-to-end —
    # per PRD Risk table: "Incorrect AI category prediction" -> user
    # correction is always allowed, and FR-04.4 defaults to "Other".
    ENABLE_IMAGE_AI: bool = True
    # Same idea as ENABLE_IMAGE_AI but for the Phase 4 Sentence Transformers
    # pipeline (app/services/embeddings.py). When False (or when
    # sentence-transformers isn't installed / weights can't be fetched),
    # text embeddings fall back to a zero-vector rather than blocking
    # report creation — FR-05.1 still runs, it just contributes no signal
    # to matching until the model is available.
    ENABLE_TEXT_AI: bool = True

    # --- Matching weights (SRS FR-08.1) — tunable without code changes ---
    WEIGHT_IMAGE: float = 0.40
    WEIGHT_TEXT: float = 0.20
    WEIGHT_CATEGORY: float = 0.10
    WEIGHT_COLOR: float = 0.10
    WEIGHT_LOCATION: float = 0.10
    WEIGHT_TIME: float = 0.05
    WEIGHT_OTHER: float = 0.05

    # --- Thresholds ---
    MATCH_NOTIFICATION_THRESHOLD: float = 70.0
    EXPLANATION_COMPONENT_THRESHOLD: float = 60.0
    DUPLICATE_SIMILARITY_THRESHOLD: float = 90.0

    TOP_K_MATCHES: int = 5

    # --- Candidate retrieval (SRS FR-07.2, Phase 5) ---
    # When True, get_candidates() orders the hard-filtered candidate set by
    # pgvector cosine distance and limits it to CANDIDATE_POOL_SIZE rows
    # *before* full weighted scoring runs (FR-07.3) — instead of scoring
    # every hard-filtered row. Safe to leave True even against sqlite/small
    # datasets: matching.py falls back to the full scan automatically
    # whenever vector ordering isn't possible (see
    # services/matching.py::_vector_prefilter_candidates).
    ENABLE_VECTOR_PREFILTER: bool = True
    CANDIDATE_POOL_SIZE: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
