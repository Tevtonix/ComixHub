from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import Optional, List
import shutil
from pathlib import Path
import uuid
import json

from app.database import get_session
from app.models import Comic, User, Chapter, Comment, Favorite
from app.routers.auth import get_current_user

router = APIRouter(prefix="/comics", tags=["comics"])
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR_COVERS = Path("static/uploads/covers")
UPLOAD_DIR_CHAPTERS = Path("static/uploads/chapters")
UPLOAD_DIR_COVERS.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR_CHAPTERS.mkdir(parents=True, exist_ok=True)


# ===== ВАЖНО: статические роуты ПЕРЕД /{comic_id} =====

@router.get("/favorites", response_class=HTMLResponse)
async def my_favorites(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    favorites = session.exec(
        select(Comic)
        .join(Favorite, Comic.id == Favorite.comic_id)
        .where(Favorite.user_id == current_user.id)
    ).all()
    return templates.TemplateResponse("favorites.html", {
        "request": request, "comics": favorites,
        "current_user": current_user, "title": "Мои закладки"
    })


@router.get("/new", response_class=HTMLResponse)
async def new_comic_form(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    if not current_user.is_author:
        raise HTTPException(status_code=403, detail="Только авторы могут создавать комиксы")
    return templates.TemplateResponse("comic_form.html", {
        "request": request, "current_user": current_user, "title": "Новый комикс"
    })


@router.get("/", response_class=HTMLResponse)
async def list_comics(
    request: Request,
    q: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    query = select(Comic).join(User, Comic.author_id == User.id)
    if q and q.strip():
        search = f"%{q.strip()}%"
        query = query.where(
            (Comic.title.ilike(search)) |
            (Comic.description.ilike(search)) |
            (User.username.ilike(search))
        )
    comics = session.exec(query).all()
    return templates.TemplateResponse("index.html", {
        "request": request, "comics": comics,
        "current_user": current_user, "title": "Все комиксы", "search_query": q or ""
    })


@router.post("/")
async def create_comic(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    cover: Optional[UploadFile] = File(None),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    if not current_user.is_author:
        raise HTTPException(status_code=403, detail="Только авторы могут создавать комиксы")
    cover_path = None
    if cover and cover.filename:
        ext = cover.filename.rsplit(".", 1)[-1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        with open(UPLOAD_DIR_COVERS / filename, "wb") as buf:
            shutil.copyfileobj(cover.file, buf)
        cover_path = f"/static/uploads/covers/{filename}"
    comic = Comic(title=title, description=description, cover_image=cover_path, author_id=current_user.id)
    session.add(comic)
    session.commit()
    session.refresh(comic)
    return RedirectResponse(url=f"/comics/{comic.id}", status_code=303)


@router.get("/{comic_id}", response_class=HTMLResponse)
async def get_comic(
    comic_id: int, request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic:
        raise HTTPException(status_code=404, detail="Комикс не найден")
    is_favorited = False
    if current_user:
        is_favorited = bool(session.exec(
            select(Favorite).where(Favorite.user_id == current_user.id, Favorite.comic_id == comic_id)
        ).first())
    return templates.TemplateResponse("comic_detail.html", {
        "request": request, "comic": comic,
        "current_user": current_user, "is_favorited": is_favorited, "title": comic.title
    })


@router.get("/{comic_id}/chapters/new", response_class=HTMLResponse)
async def new_chapter_form(
    comic_id: int, request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403, detail="Только авторы могут добавлять главы")
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic or comic.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы можете добавлять главы только к своим комиксам")
    return templates.TemplateResponse("chapter_form.html", {
        "request": request, "comic": comic, "current_user": current_user
    })


@router.post("/{comic_id}/chapters")
async def create_chapter(
    comic_id: int,
    chapter_number: int = Form(...),
    title: str = Form(...),
    pages: List[UploadFile] = File(...),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403, detail="Только авторы могут добавлять главы")
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic or comic.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы можете добавлять главы только к своим комиксам")
    chapter_dir = UPLOAD_DIR_CHAPTERS / str(comic_id) / str(chapter_number)
    chapter_dir.mkdir(parents=True, exist_ok=True)
    page_paths = []
    for page in pages:
        if page.filename:
            ext = page.filename.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4()}.{ext}"
            with open(chapter_dir / filename, "wb") as buf:
                shutil.copyfileobj(page.file, buf)
            page_paths.append(f"/static/uploads/chapters/{comic_id}/{chapter_number}/{filename}")
    session.add(Chapter(comic_id=comic_id, chapter_number=chapter_number, title=title, pages=json.dumps(page_paths)))
    session.commit()
    return RedirectResponse(url=f"/comics/{comic_id}", status_code=303)


@router.get("/{comic_id}/chapters/{chapter_id}/read", response_class=HTMLResponse)
async def read_chapter(
    comic_id: int, chapter_id: int, request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    chapter = session.exec(select(Chapter).where(Chapter.id == chapter_id)).first()
    if not chapter or chapter.comic_id != comic_id:
        raise HTTPException(status_code=404, detail="Глава не найдена")
    pages = chapter.get_pages()
    comments = session.exec(
        select(Comment).where(Comment.chapter_id == chapter_id).order_by(Comment.created_at.desc())
    ).all()
    for comment in comments:
        _ = comment.user  # lazy load
    return templates.TemplateResponse("chapter_read.html", {
        "request": request, "chapter": chapter, "pages": pages,
        "comments": comments, "current_user": current_user,
        "comic_id": comic_id, "title": f"{chapter.title} — ComixHub"
    })


@router.post("/{comic_id}/chapters/{chapter_id}/comment")
async def add_comment(
    comic_id: int, chapter_id: int,
    text: str = Form(...),
    rating: Optional[int] = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    session.add(Comment(
        chapter_id=chapter_id, user_id=current_user.id,
        text=text, rating=rating if rating else None
    ))
    session.commit()
    return RedirectResponse(url=f"/comics/{comic_id}/chapters/{chapter_id}/read", status_code=303)


@router.post("/{comic_id}/favorite")
async def toggle_favorite(
    comic_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    existing = session.exec(
        select(Favorite).where(Favorite.user_id == current_user.id, Favorite.comic_id == comic_id)
    ).first()
    if existing:
        session.delete(existing)
    else:
        session.add(Favorite(user_id=current_user.id, comic_id=comic_id))
    session.commit()
    return RedirectResponse(url=f"/comics/{comic_id}", status_code=303)