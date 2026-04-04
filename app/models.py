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