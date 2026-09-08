"""
Lazy Supabase client factory. Kept separate from config.py so importing
settings never requires the `supabase` package to actually connect —
useful for AUTH_MODE=local development where no Supabase project exists
yet (Phase 0/1 can run entirely without this being called).
"""
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_supabase_admin() -> Client:
    """
    Service-role client — full DB/Storage/Auth admin access. Never expose
    this key or client to the frontend; it's backend-only (Architecture
    Sec. 9 / SRS Security Requirements).
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to use the "
            "Supabase client. Set AUTH_MODE=local to skip Supabase entirely."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
