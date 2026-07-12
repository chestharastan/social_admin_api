from functools import lru_cache

from supabase import Client, create_client

from auth.config import SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase is not configured")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase admin client is not configured")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)