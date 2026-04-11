from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select
from typing import Optional
import shutil
from pathlib import Path
import uuid

from app.database import get_session
from app.models import Comic, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/comics", tags=["comics"])

UPLOAD_DIR = Path("static/uploads/covers")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_class=HTMLResponse)
async def list_comics(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    comics = session.exec(select(Comic)).all()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "comics": comics,
            "current_user": current_user,
            "title": "Все комиксы"
        }
    )


@router.get("/new", response_class=HTMLResponse)
async def new_comic_form(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403, detail="Только авторы могут публиковать комиксы")
    
    return templates.TemplateResponse("comic_form.html", {
        "request": request,
        "current_user": current_user
    })


@router.post("/")
async def create_comic(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    cover: UploadFile = File(None),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403, detail="Только авторы могут публиковать комиксы")

    cover_path = None
    if cover and cover.filename:
        # Создаём уникальное имя файла
        file_ext = cover.filename.split(".")[-1].lower()
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = UPLOAD_DIR / unique_name
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(cover.file, buffer)
        
        cover_path = f"/static/uploads/covers/{unique_name}"

    new_comic = Comic(
        title=title,
        description=description,
        cover_image=cover_path,
        author_id=current_user.id
    )
    
    session.add(new_comic)
    session.commit()
    session.refresh(new_comic)

    return RedirectResponse(url="/comics/", status_code=303)

@router.get("/{comic_id}", response_class=HTMLResponse)
async def get_comic(
    comic_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    
    if not comic:
        raise HTTPException(status_code=404, detail="Комикс не найден")
    
    return templates.TemplateResponse("comic_detail.html", {
        "request": request,
        "comic": comic,
        "current_user": current_user,
        "title": comic.title
    })