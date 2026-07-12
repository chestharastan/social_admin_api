import os

from dotenv import load_dotenv


load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_PROFILE_TABLE = os.getenv("SUPABASE_PROFILE_TABLE", "profiles")
SUPABASE_POST_TYPES_TABLE = os.getenv("SUPABASE_POST_TYPES_TABLE", "post_types")
SUPABASE_POSTS_TABLE = os.getenv("SUPABASE_POSTS_TABLE", "posts")
SUPABASE_POST_IMAGES_TABLE = os.getenv("SUPABASE_POST_IMAGES_TABLE", "post_images")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "website")
