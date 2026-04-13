from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import json


class User(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True)
    email: str = Field(max_length=100, unique=True, index=True)
    hashed_password: str
    is_author: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    comics: List["Comic"] = Relationship(back_populates="author")


class Comic(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: Optional[str] = None
    cover_image: Optional[str] = None
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    author: Optional["User"] = Relationship(back_populates="comics")
    chapters: List["Chapter"] = Relationship(back_populates="comic")


class Chapter(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    comic_id: int = Field(foreign_key="comic.id")
    chapter_number: int
    title: str = Field(max_length=200)
    pages: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    comic: Optional["Comic"] = Relationship(back_populates="chapters")
    comments: List["Comment"] = Relationship(back_populates="chapter")

    def get_pages(self) -> List[str]:
        if not self.pages:
            return []
        try:
            return json.loads(self.pages)
        except Exception:
            return []

    def average_rating(self) -> float:
        if not self.comments:
            return 0.0
        ratings = [c.rating for c in self.comments if c.rating is not None]
        if not ratings:
            return 0.0
        return round(sum(ratings) / len(ratings), 1)


class Comment(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    chapter_id: int = Field(foreign_key="chapter.id")
    user_id: int = Field(foreign_key="user.id")
    text: str = Field(max_length=1000)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship()
    chapter: Optional["Chapter"] = Relationship(back_populates="comments")


class Favorite(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    comic_id: int = Field(foreign_key="comic.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship()
    comic: Optional["Comic"] = Relationship()