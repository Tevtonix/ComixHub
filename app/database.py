from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker

SQLITE_URL = "sqlite:///comixhub.db"
engine = create_engine(SQLITE_URL, echo=False, connect_args={"check_same_thread": False})

def get_session() -> Session:
    with Session(engine) as session:
        yield session