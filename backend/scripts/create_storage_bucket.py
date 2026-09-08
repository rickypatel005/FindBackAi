"""
Creates the private Supabase Storage bucket used for report images
(Architecture Sec. 8 — path convention reports/{user_id}/{report_id}/{image_id}.jpg).

Run once per Supabase project, after filling in SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY in backend/.env:

    python -m scripts.create_storage_bucket
"""
from app.core.config import get_settings
from app.core.supabase_client import get_supabase_admin

settings = get_settings()


def main() -> None:
    supabase = get_supabase_admin()
    existing = {b.name for b in supabase.storage.list_buckets()}

    if settings.STORAGE_BUCKET in existing:
        print(f"Bucket '{settings.STORAGE_BUCKET}' already exists — nothing to do.")
        return

    supabase.storage.create_bucket(
        settings.STORAGE_BUCKET,
        options={
            "public": False,  # private bucket per Architecture Sec. 8
            "file_size_limit": f"{settings.MAX_IMAGE_SIZE_MB}MB",
            "allowed_mime_types": settings.ALLOWED_IMAGE_TYPES,
        },
    )
    print(f"Created private bucket '{settings.STORAGE_BUCKET}'.")


if __name__ == "__main__":
    main()
