from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from supabase_auth.errors import AuthApiError

from auth.config import SUPABASE_PROFILE_TABLE, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY, SUPABASE_URL
from auth.providers.supabase import get_supabase_admin_client, get_supabase_client
from auth.schemas import SupabaseCreateUserRequest, SupabaseProfile, SupabaseUser


supabase_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _auth_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def sign_in_with_supabase(email: str, password: str):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured",
        )

    client = get_supabase_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
    except AuthApiError as exc:
        if exc.status in (400, 401):
            raise _auth_exception("Invalid Supabase credentials") from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase authentication failed",
        ) from exc

    session = response.session

    if session is None or session.access_token is None:
        raise _auth_exception("Invalid Supabase credentials")

    return session


def get_supabase_user(token: str) -> SupabaseUser:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured",
        )

    client = get_supabase_client()
    try:
        result = client.auth.get_user(token)
    except AuthApiError as exc:
        if exc.status in (400, 401, 403):
            raise _auth_exception("Could not validate Supabase credentials") from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase authentication failed",
        ) from exc

    user = result.user

    if user is None:
        raise _auth_exception("Could not validate Supabase credentials")

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
        role=profile.get("role"),
        full_name=profile.get("full_name"),
        data=profile,
    )


def get_current_admin_user(current_user: SupabaseUser = Depends(get_current_supabase_user)) -> SupabaseUser:
    profile = get_supabase_profile(current_user.id)

    if profile.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role is required",
        )

    return current_user


def create_supabase_user(payload: SupabaseCreateUserRequest) -> SupabaseProfile:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase admin access is not configured",
        )

    client = get_supabase_admin_client()
    metadata = {"role": payload.role}
    if payload.full_name:
        metadata["full_name"] = payload.full_name

    try:
        response = client.auth.admin.create_user(
            {
                "email": str(payload.email),
                "password": payload.password,
                "email_confirm": payload.email_confirm,
                "user_metadata": metadata,
            }
        )
    except AuthApiError as exc:
        if exc.code in ("email_exists", "user_already_exists") or exc.status == 422:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Supabase user already exists",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase user creation failed",
        ) from exc

    user = response.user

    profile_data = {
        "id": user.id,
        "email": user.email,
        "role": payload.role,
        "full_name": payload.full_name,
    }
    profile_response = client.table(SUPABASE_PROFILE_TABLE).upsert(profile_data).execute()
    rows = profile_response.data or []
    profile = rows[0] if rows else profile_data

    return SupabaseProfile(
        id=profile.get("id"),
        email=profile.get("email"),
        role=profile.get("role"),
        full_name=profile.get("full_name"),
        data=profile,
    )
