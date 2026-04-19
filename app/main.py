from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Session, select

from app.database import engine, get_session
from app.routers import comics, auth
from app.routers.profile import router as profile_router
from app.routers.auth import get_current_user
from app.models import Comic, User

app = FastAPI(title="ComixHub")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

SQLModel.metadata.create_all(bind=engine)

app.include_router(comics.router)
app.include_router(auth.router)
app.include_router(profile_router)


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session)
):
    comic_list = session.exec(
        select(Comic).join(User, Comic.author_id == User.id)
        .order_by(Comic.created_at.desc()).limit(12)
    ).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Главная",
        "current_user": current_user,
        "comics": comic_list,
        "search_query": "",
        "page": 1,
        "total_pages": 1,
        "total": len(comic_list),
    })