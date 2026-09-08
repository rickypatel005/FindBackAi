"""
Supabase Auth path for register/login. Used when AUTH_MODE=supabase.

Sign-up/sign-in are delegated entirely to Supabase Auth — this backend
never stores or sees a raw password in this mode. The profile row in
`public.users` (role, name) is created automatically by the database
trigger in migrations/002_auth_trigger.sql the moment Supabase Auth
creates the corresponding `auth.users` row, so this module just re-reads
it afterward.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.supabase_client import get_supabase_admin
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut


def register_via_supabase(db: Session, payload: RegisterRequest) -> TokenResponse:
    supabase = get_supabase_admin()

    try:
        result = supabase.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": {"data": {"name": payload.name}} if payload.name else {},
            }
        )
    except Exception as exc:  # supabase-py raises its own AuthApiError
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if result.user is None or result.session is None:
        # Common case: email confirmation is required before a session is
        # issued. Surface that plainly rather than pretending it succeeded.
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Registered — check your email to confirm your account before logging in.",
        )

    profile = db.query(User).filter(User.id == result.user.id).first()
    if profile is None:
        # Trigger should have created this row already; this is a fallback
        # in case the trigger migration hasn't been applied yet.
        profile = User(id=result.user.id, email=payload.email, name=payload.name)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return TokenResponse(access_token=result.session.access_token, user=UserOut.model_validate(profile))


def login_via_supabase(db: Session, payload: LoginRequest) -> TokenResponse:
    supabase = get_supabase_admin()

    try:
        result = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    profile = db.query(User).filter(User.id == result.user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User profile not found")

    return TokenResponse(access_token=result.session.access_token, user=UserOut.model_validate(profile))
