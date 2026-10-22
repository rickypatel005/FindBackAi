from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth_supabase import login_via_supabase, register_via_supabase

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

# --- AUTH_MODE=local path -------------------------------------------------
# A minimal standalone auth path so the API is fully runnable and testable
# before a Supabase project exists (Phase 0/1 setup). Switching AUTH_MODE
# to "supabase" in .env routes register/login through
# app/services/auth_supabase.py instead — no other code changes needed,
# since every other route only depends on the JWT + the `User` row, not on
# how the token was issued.


def _register_local(payload: RegisterRequest, db: Session) -> TokenResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        name=payload.name,
        role=RoleEnum.USER,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


def _login_local(payload: LoginRequest, db: Session) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


# --- Routes ----------------------------------------------------------------
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if settings.AUTH_MODE == "supabase":
        return register_via_supabase(db, payload)
    return _register_local(payload, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    if settings.AUTH_MODE == "supabase":
        return login_via_supabase(db, payload)
    return _login_local(payload, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    # Stateless JWT: logout is enforced client-side (FR-01.3) by discarding
    # the token. Nothing to invalidate server-side in this MVP.
    return None


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
