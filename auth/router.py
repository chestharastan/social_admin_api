from fastapi import APIRouter, Depends, HTTPException, status

from auth.schemas import SupabaseLoginRequest, SupabaseProfile, SupabaseSession, SupabaseUser
from auth.service import get_current_supabase_user, get_supabase_profile, sign_in_with_supabase


router = APIRouter()


@router.post("/login", response_model=SupabaseSession, summary="Sign in with Supabase", description="Authenticate a user against Supabase Auth and return the Supabase session tokens.")
def login(credentials: SupabaseLoginRequest):
    session = sign_in_with_supabase(credentials.email, credentials.password)
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=SupabaseUser, summary="Get authenticated user", description="Return the Supabase user associated with the provided bearer token.")
def me(current_user: SupabaseUser = Depends(get_current_supabase_user)):
    return current_user


@router.get("/me/profile", response_model=SupabaseProfile, summary="Get auth profile", description="Fetch the user's row from the configured Supabase profile table.")
def me_profile(current_user: SupabaseUser = Depends(get_current_supabase_user)):
    return get_supabase_profile(current_user.id)