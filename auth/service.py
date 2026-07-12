from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from auth.config import SUPABASE_PROFILE_TABLE, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY, SUPABASE_URL
from auth.providers.supabase import get_supabase_admin_client, get_supabase_client
from auth.schemas import SupabaseProfile, SupabaseUser


supabase_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/supabase/login")


def sign_in_with_supabase(email: str, password: str):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured",
        )

    client = get_supabase_client()
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    session = response.session

    if session is None or session.access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Supabase credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return session


def get_supabase_user(token: str) -> SupabaseUser:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured",
        )

    client = get_supabase_client()
    result = client.auth.get_user(token)
    user = result.user

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Supabase credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return SupabaseUser(id=user.id, email=user.email)


def get_current_supabase_user(token: str = Depends(supabase_oauth2_scheme)) -> SupabaseUser:
    return get_supabase_user(token)


def get_supabase_profile(user_id: str) -> SupabaseProfile:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase admin access is not configured",
        )

    client = get_supabase_admin_client()
    response = client.table(SUPABASE_PROFILE_TABLE).select("*").eq("id", user_id).limit(1).execute()
    rows = response.data or []

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    profile = rows[0]
    return SupabaseProfile(
        id=profile.get("id"),
        email=profile.get("email"),
        data=profile,
    )