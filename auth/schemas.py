from typing import Dict, Optional

from pydantic import BaseModel


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


class SupabaseProfile(BaseModel):
    id: str
    email: Optional[str] = None
    data: Optional[Dict[str, object]] = None