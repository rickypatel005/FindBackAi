"""
Auth helpers. In production, Supabase Auth issues the session/JWT (per
Architecture Sec. 9); this module verifies that JWT on every protected
route and exposes role-based dependencies. A local password-hash path is
also included so the API is runnable standalone (e.g. local dev without
Supabase) without changing the contract.
"""
import datetime
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import RoleEnum, User

settings = get_settings()
# pbkdf2_sha256 avoids the bcrypt-vs-passlib version-detection breakage that
# ships with recent `bcrypt` releases (no C-extension version coupling).
# Password strength itself is enforced by Supabase Auth in AUTH_MODE=supabase
# (SRS FR-01.5); this hashing only matters for the local-dev auth path.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: uuid.UUID, role: RoleEnum) -> str:
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    payload = {"sub": str(user_id), "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Verifies a session JWT. In AUTH_MODE=supabase, the token was issued by
    Supabase Auth and is verified against SUPABASE_JWT_SECRET (the
    project's JWT secret, not the anon/service keys) with the standard
    "authenticated" audience Supabase sets. In AUTH_MODE=local, it's a
    token this backend issued itself in create_access_token().
    """
    try:
        if settings.AUTH_MODE == "supabase":
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    # Supabase tokens key the subject as "sub" too (the auth.users.id uuid),
    # which is the same id used for the linked public.users profile row
    # created by the on-signup trigger (migrations/002_auth_trigger.sql).
    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session subject")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """SRS Section 7: admin routes reject non-admin callers with 403."""
    if user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user
