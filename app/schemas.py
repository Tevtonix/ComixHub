from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ComicCreate(BaseModel):
    title: str
    description: Optional[str] = None

class ComicRead(ComicCreate):
    id: int
    created_at: datetime