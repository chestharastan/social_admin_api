from typing import Dict, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


UserRole = Literal["admin", "manager"]


class Token(BaseModel):
    access_token: str
    token_type: str


class SupabaseSession(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class SupabaseUser(BaseModel):
    id: str
    email: Optional[str] = None
    profile: Optional[Dict[str, object]] = None


class SupabaseLoginRequest(BaseModel):
    email: str
    password: str


class SupabaseCreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: UserRole
    full_name: Optional[str] = None
    email_confirm: bool = True


class SupabaseProfile(BaseModel):
    id: str
    email: Optional[str] = None
    role: Optional[UserRole] = None
    full_name: Optional[str] = None
    data: Optional[Dict[str, object]] = None
