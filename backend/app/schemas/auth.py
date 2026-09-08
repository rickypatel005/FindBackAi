import uuid

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import RoleEnum


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str | None
    role: RoleEnum


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
