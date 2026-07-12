from fastapi import APIRouter, Depends, status

from auth.schemas import (
    SupabaseCreateUserRequest,
    SupabaseLoginRequest,
    SupabaseProfile,
    SupabaseRefreshRequest,
    SupabaseSession,
    SupabaseUser,
)
from auth.service import (
    create_supabase_user,
    get_current_admin_user,
    get_current_supabase_user,
    get_supabase_profile,
    refresh_supabase_session,
    sign_in_with_supabase,
)


router = APIRouter()


@router.post(
    "/login",
    response_model=SupabaseSession,
    summary="Login",
)
def login(credentials: SupabaseLoginRequest):
    return sign_in_with_supabase(credentials.email, credentials.password)


@router.post(
    "/refresh",
    response_model=SupabaseSession,
    summary="Refresh token",
)
def refresh_token(payload: SupabaseRefreshRequest):
    return refresh_supabase_session(payload)


@router.get(
    "/me",
    response_model=SupabaseUser,
    summary="Current user",
)
def me(current_user: SupabaseUser = Depends(get_current_supabase_user)):
    return current_user


@router.get(
    "/me/profile",
    response_model=SupabaseProfile,
    summary="Current user profile",
)
def me_profile(current_user: SupabaseUser = Depends(get_current_supabase_user)):
    return get_supabase_profile(current_user.id)


@router.post(
    "/users",
    response_model=SupabaseProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
def create_user(
    payload: SupabaseCreateUserRequest,
    _: SupabaseUser = Depends(get_current_admin_user),
):
    return create_supabase_user(payload)
