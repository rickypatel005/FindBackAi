import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.session import Base


class RoleEnum(str, enum.Enum):
    USER = "User"
    ADMIN = "Admin"


class User(Base):
    """
    Mirrors Supabase `auth.users` via a linked profile row (SRS Section 2).
    Role is stored server-side and never inferred from the frontend.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
