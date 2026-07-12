from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from auth.schemas import SupabaseUser
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
from posts.service import (
    add_post_image,
    create_post,
    delete_post,
    delete_post_image,
    get_current_post_editor,
    get_post,
    get_post_by_slug,
    list_post_types,
    list_posts,
    update_post,
    update_post_image,
    upload_post_image,
)


router = APIRouter()


@router.get(
    "/types",
    response_model=List[PostType],
    summary="List post types",
)
def post_types():
    return list_post_types()


@router.get(
    "",
    response_model=List[Post],
    summary="List published posts",
)
def public_posts(
    featured: Optional[bool] = None,
    type_id: Optional[int] = None,
    type_slug: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return list_posts(
        published=True,
        featured=featured,
        type_id=type_id,
        type_slug=type_slug,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/admin",
    response_model=List[Post],
    summary="List posts for admin dashboard",
)
def admin_posts(
    published: Optional[bool] = None,
    featured: Optional[bool] = None,
    type_id: Optional[int] = None,
    type_slug: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: SupabaseUser = Depends(get_current_post_editor),
):
    return list_posts(
        published=published,
        featured=featured,
        type_id=type_id,
        type_slug=type_slug,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/admin/{post_id}",
    response_model=Post,
    summary="Get a post for admin dashboard",
)
def admin_post(
    post_id: UUID,
    _: SupabaseUser = Depends(get_current_post_editor),
):
    return get_post(post_id, published_only=False)


@router.get(
    "/slug/{slug}",
    response_model=Post,
    summary="Get published post by slug",
)
def public_post_by_slug(slug: str):
    return get_post_by_slug(slug, published_only=True)


@router.post(
    "/uploads/covers",
    response_model=PostImageUpload,
    summary="Upload cover image",
)
async def upload_cover_image(
    file: UploadFile = File(...),
    _: SupabaseUser = Depends(get_current_post_editor),
):
    return upload_post_image(
        folder="covers",
        filename=file.filename or "cover",
        content=await file.read(),
        content_type=file.content_type,
    )


@router.post(
    "/uploads/gallery",
    response_model=PostImageUpload,
    summary="Upload gallery image",
)
async def upload_gallery_image(
    file: UploadFile = File(...),
    _: SupabaseUser = Depends(get_current_post_editor),
):
    return upload_post_image(
        folder="gallery",
        filename=file.filename or "gallery",
        content=await file.read(),
        content_type=file.content_type,
    )


@router.post(
    "/{post_id}/cover",
    response_model=Post,
    summary="Upload and set cover image",
)
async def upload_post_cover_image(
    post_id: UUID,
    file: UploadFile = File(...),
    _: SupabaseUser = Depends(get_current_post_editor),
):
    upload = upload_post_image(
        folder="covers",
        filename=file.filename or "cover",
        content=await file.read(),
        content_type=file.content_type,
    )
    return update_post(post_id, PostUpdate(cover_image=upload.path))


@router.post(
    "/{post_id}/images/upload",
    response_model=PostImage,
    status_code=status.HTTP_201_CREATED,
    summary="Upload one gallery image",
)
async def upload_one_gallery_image(
    post_id: UUID,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(default=None),
    sort_order: Optional[int] = Form(default=None, ge=0),
    _: SupabaseUser = Depends(get_current_post_editor),
):
    upload = upload_post_image(
        folder="gallery",
        filename=file.filename or "gallery",
        content=await file.read(),
        content_type=file.content_type,
    )
    return add_post_image(
        post_id,
        PostImageCreate(
            image_path=upload.path,
            caption=caption,
            sort_order=sort_order,
        ),
    )


@router.post(
    "/{post_id}/images/uploads",
    response_model=List[PostImage],
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple gallery images",
)
async def upload_multiple_gallery_images(
    post_id: UUID,
    files: List[UploadFile] = File(...),
    _: SupabaseUser = Depends(get_current_post_editor),
):
    created_images = []
    for file in files:
        upload = upload_post_image(
            folder="gallery",
            filename=file.filename or "gallery",
            content=await file.read(),
            content_type=file.content_type,
        )
        created_images.append(
            add_post_image(
                post_id,
                PostImageCreate(image_path=upload.path),
            )
        )

    return created_images


@router.get(
    "/{post_id}",
    response_model=Post,
    summary="Get published post by id",
)
def public_post(post_id: UUID):
    return get_post(post_id, published_only=True)


@router.post(
    "",
    response_model=Post,
    status_code=status.HTTP_201_CREATED,
    summary="Create post",
)
def create_post_endpoint(
    payload: PostCreate,
    current_user: SupabaseUser = Depends(get_current_post_editor),
):
    return create_post(payload, current_user.id)


@router.patch(
    "/{post_id}",
    response_model=Post,
    summary="Update post",
)
def update_post_endpoint(
    post_id: UUID,
    payload: PostUpdate,
    _: SupabaseUser = Depends(get_current_post_editor),
):
    return update_post(post_id, payload)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete post",
)
def delete_post_endpoint(
    post_id: UUID,
    _: SupabaseUser = Depends(get_current_post_editor),
):
    delete_post(post_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{post_id}/images",
    response_model=PostImage,
    status_code=status.HTTP_201_CREATED,
    summary="Add gallery image",
)
def add_post_image_endpoint(
    post_id: UUID,
    payload: PostImageCreate,
    _: SupabaseUser = Depends(get_current_post_editor),
):
    return add_post_image(post_id, payload)


@router.patch(
    "/{post_id}/images/{image_id}",
    response_model=PostImage,
    summary="Update gallery image",
)
def update_post_image_endpoint(
    post_id: UUID,
    image_id: UUID,
    payload: PostImageUpdate,
    _: SupabaseUser = Depends(get_current_post_editor),
):
    return update_post_image(post_id, image_id, payload)


@router.delete(
    "/{post_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete gallery image",
)
def delete_post_image_endpoint(
    post_id: UUID,
    image_id: UUID,
    _: SupabaseUser = Depends(get_current_post_editor),
):
    delete_post_image(post_id, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
