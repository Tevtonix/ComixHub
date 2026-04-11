from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class ComicBase(SQLModel):
    title: str = Field(max_length=200)
    description: Optional[str] = None
    author_id: Optional[int] = None          # → потом ForeignKey на User

class Comic(ComicBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True)
    email: str = Field(max_length=100, unique=True, index=True)
    hashed_password: str
    is_author: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Comic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: Optional[str] = None
    cover_image: Optional[str] = None          # ← новое поле: путь к обложке
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Chapter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    comic_id: int = Field(foreign_key="comic.id")
    chapter_number: int
    title: str = Field(max_length=200)
    # Для хранения страниц будем использовать JSON поле (список путей к изображениям)
    pages: Optional[str] = Field(default=None)   # храним как JSON строку: ["path1.jpg", "path2.jpg", ...]
    created_at: datetime = Field(default_factory=datetime.utcnow)