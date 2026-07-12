import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, status
from postgrest.exceptions import APIError
from storage3.exceptions import StorageApiError

from auth.config import (
    SUPABASE_POST_IMAGES_TABLE,
    SUPABASE_POST_TYPES_TABLE,
    SUPABASE_POSTS_TABLE,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_URL,
)
from auth.providers.supabase import get_supabase_admin_client
from auth.schemas import SupabaseUser
from auth.service import get_current_supabase_user, get_supabase_profile
from posts.schemas import (
    Post,
    PostCreate,
    PostImage,
    PostImageCreate,
    PostImageUpload,
    PostImageUpdate,
    PostType,
    PostUpdate,
)


ALLOWED_IMAGE_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/webp",
}
MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024


def _require_supabase_admin_config() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase admin access is not configured",
        )


def get_current_post_editor(
    current_user: SupabaseUser = Depends(get_current_supabase_user),
) -> SupabaseUser:
    profile = get_supabase_profile(current_user.id)

    if profile.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager role is required",
        )

    return current_user


def _db_error(exc: APIError) -> HTTPException:
    code = getattr(exc, "code", None)
    detail = getattr(exc, "message", None) or str(exc)

    if code == "23505":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A row with this unique value already exists",
        )
    if code == "23503":
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referenced row does not exist",
        )

    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Supabase database request failed: {detail}",
    )


def _client():
    _require_supabase_admin_config()
    return get_supabase_admin_client()


def _storage_error(exc: StorageApiError) -> HTTPException:
    detail = getattr(exc, "message", None) or str(exc)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Supabase storage request failed: {detail}",
    )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "post"


def _safe_file_name(filename: str) -> str:
    stem = Path(filename).stem or "image"
    suffix = Path(filename).suffix.lower()
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-") or "image"
    return f"{uuid4()}-{safe_stem}{suffix}"


def _post_type_from_row(row: dict) -> PostType:
    return PostType(id=row["id"], name=row["name"], slug=row["slug"])


def _image_from_row(row: dict) -> PostImage:
    return PostImage(**row)


def _post_from_row(
    row: dict,
    post_type: Optional[PostType] = None,
    images: Optional[List[PostImage]] = None,
) -> Post:
    return Post(
        **row,
        type=post_type,
        images=images or [],
    )


def _get_post_type(type_id: int) -> PostType:
    client = _client()
    try:
        response = (
            client.table(SUPABASE_POST_TYPES_TABLE)
            .select("*")
            .eq("id", type_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post type does not exist",
        )

    return _post_type_from_row(rows[0])


def _get_post_type_by_slug(slug: str) -> PostType:
    client = _client()
    try:
        response = (
            client.table(SUPABASE_POST_TYPES_TABLE)
            .select("*")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post type not found",
        )

    return _post_type_from_row(rows[0])


def _type_map_for_rows(rows: Iterable[dict]) -> Dict[int, PostType]:
    type_ids = sorted({row["type_id"] for row in rows})
    if not type_ids:
        return {}

    client = _client()
    try:
        response = (
            client.table(SUPABASE_POST_TYPES_TABLE)
            .select("*")
            .in_("id", type_ids)
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    return {row["id"]: _post_type_from_row(row) for row in response.data or []}


def _images_for_post_ids(post_ids: Iterable[str]) -> Dict[str, List[PostImage]]:
    ids = list(post_ids)
    if not ids:
        return {}

    client = _client()
    try:
        response = (
            client.table(SUPABASE_POST_IMAGES_TABLE)
            .select("*")
            .in_("post_id", ids)
            .order("sort_order")
            .order("created_at")
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    image_map: Dict[str, List[PostImage]] = {post_id: [] for post_id in ids}
    for row in response.data or []:
        image_map.setdefault(row["post_id"], []).append(_image_from_row(row))

    return image_map


def _posts_from_rows(rows: List[dict]) -> List[Post]:
    type_map = _type_map_for_rows(rows)
    image_map = _images_for_post_ids([row["id"] for row in rows])

    return [
        _post_from_row(
            row,
            post_type=type_map.get(row["type_id"]),
            images=image_map.get(row["id"], []),
        )
        for row in rows
    ]


def list_post_types() -> List[PostType]:
    client = _client()
    try:
        response = (
            client.table(SUPABASE_POST_TYPES_TABLE)
            .select("*")
            .order("id")
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    return [_post_type_from_row(row) for row in response.data or []]


def upload_post_image(
    *,
    folder: str,
    filename: str,
    content: bytes,
    content_type: Optional[str],
) -> PostImageUpload:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, WebP, GIF, and SVG image uploads are allowed",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    if len(content) > MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image upload is larger than 10 MB",
        )

    path = f"posts/{folder}/{_safe_file_name(filename)}"
    bucket = _client().storage.from_(SUPABASE_STORAGE_BUCKET)

    try:
        bucket.upload(
            path,
            content,
            {
                "content-type": content_type,
                "cache-control": "3600",
                "upsert": "false",
            },
        )
    except StorageApiError as exc:
        raise _storage_error(exc) from exc

    return PostImageUpload(
        bucket=SUPABASE_STORAGE_BUCKET,
        path=path,
        content_type=content_type,
    )


def list_posts(
    *,
    published: Optional[bool],
    featured: Optional[bool],
    type_id: Optional[int],
    type_slug: Optional[str],
    limit: int,
    offset: int,
) -> List[Post]:
    client = _client()
    query = client.table(SUPABASE_POSTS_TABLE).select("*")

    if published is not None:
        query = query.eq("published", published)
    if featured is not None:
        query = query.eq("featured", featured)
    if type_id is not None:
        query = query.eq("type_id", type_id)
    if type_slug is not None:
        query = query.eq("type_id", _get_post_type_by_slug(type_slug).id)

    try:
        response = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    return _posts_from_rows(response.data or [])


def get_post(post_id: UUID, *, published_only: bool) -> Post:
    client = _client()
    query = (
        client.table(SUPABASE_POSTS_TABLE)
        .select("*")
        .eq("id", str(post_id))
        .limit(1)
    )
    if published_only:
        query = query.eq("published", True)

    try:
        response = query.execute()
    except APIError as exc:
        raise _db_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return _posts_from_rows([rows[0]])[0]


def get_post_by_slug(slug: str, *, published_only: bool) -> Post:
    client = _client()
    query = (
        client.table(SUPABASE_POSTS_TABLE)
        .select("*")
        .eq("slug", slug)
        .limit(1)
    )
    if published_only:
        query = query.eq("published", True)

    try:
        response = query.execute()
    except APIError as exc:
        raise _db_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return _posts_from_rows([rows[0]])[0]


def _insert_images(post_id: UUID, images: List[PostImageCreate]) -> List[PostImage]:
    if not images:
        return []

    rows = []
    for index, image in enumerate(images):
        rows.append(
            {
                "post_id": str(post_id),
                "image_path": image.image_path,
                "caption": image.caption,
                "sort_order": image.sort_order if image.sort_order is not None else index,
            }
        )

    client = _client()
    try:
        response = client.table(SUPABASE_POST_IMAGES_TABLE).insert(rows).execute()
    except APIError as exc:
        raise _db_error(exc) from exc

    return [_image_from_row(row) for row in response.data or []]


def _next_image_sort_order(post_id: UUID) -> int:
    client = _client()
    try:
        response = (
            client.table(SUPABASE_POST_IMAGES_TABLE)
            .select("sort_order")
            .eq("post_id", str(post_id))
            .order("sort_order", desc=True)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    rows = response.data or []
    if not rows:
        return 0

    return rows[0]["sort_order"] + 1


def create_post(payload: PostCreate, created_by: str) -> Post:
    _get_post_type(payload.type_id)

    row = {
        "title": payload.title,
        "slug": payload.slug or _slugify(payload.title),
        "content": payload.content,
        "type_id": payload.type_id,
        "cover_image": payload.cover_image,
        "published": payload.published,
        "featured": payload.featured,
        "created_by": created_by,
    }

    client = _client()
    try:
        response = client.table(SUPABASE_POSTS_TABLE).insert(row).execute()
    except APIError as exc:
        raise _db_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase did not return the created post",
        )

    post_id = UUID(rows[0]["id"])
    _insert_images(post_id, payload.images)
    return get_post(post_id, published_only=False)


def update_post(post_id: UUID, payload: PostUpdate) -> Post:
    update_data = payload.model_dump(exclude_unset=True, exclude={"images"})

    if "type_id" in update_data:
        _get_post_type(update_data["type_id"])
    if "slug" in update_data and update_data["slug"] is None:
        current_post = get_post(post_id, published_only=False)
        update_data["slug"] = _slugify(update_data.get("title") or current_post.title)

    if update_data:
        client = _client()
        try:
            response = (
                client.table(SUPABASE_POSTS_TABLE)
                .update(update_data)
                .eq("id", str(post_id))
                .execute()
            )
        except APIError as exc:
            raise _db_error(exc) from exc

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
    else:
        get_post(post_id, published_only=False)

    if payload.images is not None:
        client = _client()
        try:
            client.table(SUPABASE_POST_IMAGES_TABLE).delete().eq(
                "post_id", str(post_id)
            ).execute()
        except APIError as exc:
            raise _db_error(exc) from exc
        _insert_images(post_id, payload.images)

    return get_post(post_id, published_only=False)


def delete_post(post_id: UUID) -> None:
    client = _client()
    try:
        response = (
            client.table(SUPABASE_POSTS_TABLE)
            .delete()
            .eq("id", str(post_id))
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )


def add_post_image(post_id: UUID, payload: PostImageCreate) -> PostImage:
    get_post(post_id, published_only=False)
    if payload.sort_order is None:
        payload = PostImageCreate(
            image_path=payload.image_path,
            caption=payload.caption,
            sort_order=_next_image_sort_order(post_id),
        )
    image = _insert_images(post_id, [payload])
    return image[0]


def update_post_image(
    post_id: UUID,
    image_id: UUID,
    payload: PostImageUpdate,
) -> PostImage:
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return get_post_image(post_id, image_id)

    client = _client()
    try:
        response = (
            client.table(SUPABASE_POST_IMAGES_TABLE)
            .update(update_data)
            .eq("id", str(image_id))
            .eq("post_id", str(post_id))
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post image not found",
        )

    return _image_from_row(rows[0])


def get_post_image(post_id: UUID, image_id: UUID) -> PostImage:
    client = _client()
    try:
        response = (
            client.table(SUPABASE_POST_IMAGES_TABLE)
            .select("*")
            .eq("id", str(image_id))
            .eq("post_id", str(post_id))
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post image not found",
        )

    return _image_from_row(rows[0])


def delete_post_image(post_id: UUID, image_id: UUID) -> None:
    client = _client()
    try:
        response = (
            client.table(SUPABASE_POST_IMAGES_TABLE)
            .delete()
            .eq("id", str(image_id))
            .eq("post_id", str(post_id))
            .execute()
        )
    except APIError as exc:
        raise _db_error(exc) from exc

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post image not found",
        )
