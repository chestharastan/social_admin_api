from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PostType(BaseModel):
    id: int
    name: str
    slug: str


class PostImageBase(BaseModel):
    image_path: str = Field(min_length=1)
    caption: Optional[str] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


class PostImageCreate(PostImageBase):
    pass


class PostImageUpdate(BaseModel):
    image_path: Optional[str] = Field(default=None, min_length=1)
    caption: Optional[str] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


class PostImage(BaseModel):
    id: UUID
    post_id: UUID
    image_path: str
    caption: Optional[str] = None
    sort_order: int = 0
    created_at: datetime


class PostImageUpload(BaseModel):
    bucket: str
    path: str
    content_type: str


class PostCreate(BaseModel):
    title: str = Field(min_length=1)
    slug: Optional[str] = Field(default=None, min_length=1)
    content: str = Field(min_length=1)
    type_id: int
    cover_image: Optional[str] = None
    published: bool = False
    featured: bool = False
    images: List[PostImageCreate] = Field(default_factory=list)


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    slug: Optional[str] = Field(default=None, min_length=1)
    content: Optional[str] = Field(default=None, min_length=1)
    type_id: Optional[int] = None
    cover_image: Optional[str] = None
    published: Optional[bool] = None
    featured: Optional[bool] = None
    images: Optional[List[PostImageCreate]] = None


class Post(BaseModel):
    id: UUID
    title: str
    slug: str
    content: str
    type_id: int
    cover_image: Optional[str] = None
    published: bool
    featured: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    type: Optional[PostType] = None
    images: List[PostImage] = Field(default_factory=list)
