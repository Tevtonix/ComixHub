from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import Optional, List
import shutil
from pathlib import Path
import uuid
import json
import math

from app.database import get_session
from app.models import Comic, User, Chapter, Comment, Favorite
from app.routers.auth import get_current_user

router = APIRouter(prefix="/comics", tags=["comics"])
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR_COVERS = Path("static/uploads/covers")
UPLOAD_DIR_CHAPTERS = Path("static/uploads/chapters")
UPLOAD_DIR_COVERS.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR_CHAPTERS.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
PAGE_SIZE = 12


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS


def save_upload(file: UploadFile, directory: Path) -> str:
    """Save uploaded file, return relative URL path."""
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый формат «{file.filename}». Разрешены: jpg, jpeg, png, webp, gif"
        )
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / filename, "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    return f"/static/{directory.relative_to(Path('static'))}/{filename}"


# ── Статические роуты ПЕРЕД /{comic_id} ──────────────────────────────────────

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


# ── Список + пагинация ────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def list_comics(
    request: Request,
    q: Optional[str] = None,
    page: int = 1,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    base_query = select(Comic).join(User, Comic.author_id == User.id)
    if q and q.strip():
        s = f"%{q.strip()}%"
        base_query = base_query.where(
            (Comic.title.ilike(s)) | (Comic.description.ilike(s)) | (User.username.ilike(s))
        )
    all_comics = session.exec(base_query).all()
    total = len(all_comics)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PAGE_SIZE
    comics = session.exec(
        base_query.order_by(Comic.created_at.desc()).offset(offset).limit(PAGE_SIZE)
    ).all()
    return templates.TemplateResponse("index.html", {
        "request": request, "comics": comics, "current_user": current_user,
        "title": "Все комиксы", "search_query": q or "",
        "page": page, "total_pages": total_pages, "total": total,
    })


# ── Создание комикса ──────────────────────────────────────────────────────────

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
        raise HTTPException(status_code=403)
    cover_path = None
    if cover and cover.filename:
        cover_path = save_upload(cover, UPLOAD_DIR_COVERS)
    comic = Comic(title=title, description=description, cover_image=cover_path, author_id=current_user.id)
    session.add(comic)
    session.commit()
    session.refresh(comic)
    return RedirectResponse(url=f"/comics/{comic.id}", status_code=303)


# ── Детальная страница ────────────────────────────────────────────────────────

@router.get("/{comic_id}", response_class=HTMLResponse)
async def get_comic(
    comic_id: int, request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic:
        raise HTTPException(status_code=404)
    is_favorited = False
    if current_user:
        is_favorited = bool(session.exec(
            select(Favorite).where(
                Favorite.user_id == current_user.id,
                Favorite.comic_id == comic_id
            )
        ).first())
    return templates.TemplateResponse("comic_detail.html", {
        "request": request, "comic": comic,
        "current_user": current_user, "is_favorited": is_favorited, "title": comic.title
    })


# ── Форма добавления главы ────────────────────────────────────────────────────

@router.get("/{comic_id}/chapters/new", response_class=HTMLResponse)
async def new_chapter_form(
    comic_id: int, request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403)
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic or comic.author_id != current_user.id:
        raise HTTPException(status_code=403)
    return templates.TemplateResponse("chapter_form.html", {
        "request": request, "comic": comic, "chapter": None,
        "current_user": current_user, "existing_pages": [], "title": "Новая глава"
    })


# ── Создание главы ────────────────────────────────────────────────────────────

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
        raise HTTPException(status_code=403)
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic or comic.author_id != current_user.id:
        raise HTTPException(status_code=403)
    page_paths = []
    chapter_dir = UPLOAD_DIR_CHAPTERS / str(comic_id) / str(chapter_number)
    for page in pages:
        if page.filename:
            url = save_upload(page, chapter_dir)
            page_paths.append(url)
    session.add(Chapter(
        comic_id=comic_id, chapter_number=chapter_number,
        title=title, pages=json.dumps(page_paths)
    ))
    session.commit()
    return RedirectResponse(url=f"/comics/{comic_id}", status_code=303)


# ── Форма редактирования главы ────────────────────────────────────────────────

@router.get("/{comic_id}/chapters/{chapter_id}/edit", response_class=HTMLResponse)
async def edit_chapter_form(
    comic_id: int, chapter_id: int, request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403)
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic or comic.author_id != current_user.id:
        raise HTTPException(status_code=403)
    chapter = session.exec(select(Chapter).where(Chapter.id == chapter_id)).first()
    if not chapter or chapter.comic_id != comic_id:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("chapter_form.html", {
        "request": request, "comic": comic, "chapter": chapter,
        "existing_pages": chapter.get_pages(),
        "current_user": current_user, "title": "Редактировать главу"
    })


# ── Сохранение редактирования главы ──────────────────────────────────────────

@router.post("/{comic_id}/chapters/{chapter_id}/edit")
async def edit_chapter(
    comic_id: int, chapter_id: int,
    chapter_number: int = Form(...),
    title: str = Form(...),
    pages: Optional[List[UploadFile]] = File(None),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403)
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic or comic.author_id != current_user.id:
        raise HTTPException(status_code=403)
    chapter = session.exec(select(Chapter).where(Chapter.id == chapter_id)).first()
    if not chapter or chapter.comic_id != comic_id:
        raise HTTPException(status_code=404)
    chapter.chapter_number = chapter_number
    chapter.title = title
    new_files = [p for p in (pages or []) if p and p.filename]
    if new_files:
        chapter_dir = UPLOAD_DIR_CHAPTERS / str(comic_id) / str(chapter_number)
        page_paths = []
        for page in new_files:
            url = save_upload(page, chapter_dir)
            page_paths.append(url)
        chapter.pages = json.dumps(page_paths)
    session.add(chapter)
    session.commit()
    return RedirectResponse(url=f"/comics/{comic_id}", status_code=303)


# ── Удаление главы ────────────────────────────────────────────────────────────

@router.post("/{comic_id}/chapters/{chapter_id}/delete")
async def delete_chapter(
    comic_id: int, chapter_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403)
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic or comic.author_id != current_user.id:
        raise HTTPException(status_code=403)
    chapter = session.exec(select(Chapter).where(Chapter.id == chapter_id)).first()
    if not chapter or chapter.comic_id != comic_id:
        raise HTTPException(status_code=404)
    for c in session.exec(select(Comment).where(Comment.chapter_id == chapter_id)).all():
        session.delete(c)
    session.delete(chapter)
    session.commit()
    return RedirectResponse(url=f"/comics/{comic_id}", status_code=303)


# ── Чтение главы ──────────────────────────────────────────────────────────────

@router.get("/{comic_id}/chapters/{chapter_id}/read", response_class=HTMLResponse)
async def read_chapter(
    comic_id: int, chapter_id: int, request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    chapter = session.exec(select(Chapter).where(Chapter.id == chapter_id)).first()
    if not chapter or chapter.comic_id != comic_id:
        raise HTTPException(status_code=404)
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()

    all_chapters = session.exec(
        select(Chapter).where(Chapter.comic_id == comic_id).order_by(Chapter.chapter_number)
    ).all()
    idx = next((i for i, c in enumerate(all_chapters) if c.id == chapter_id), -1)
    prev_chapter = all_chapters[idx - 1] if idx > 0 else None
    next_chapter = all_chapters[idx + 1] if idx < len(all_chapters) - 1 else None

    pages = chapter.get_pages()
    comments = session.exec(
        select(Comment).where(Comment.chapter_id == chapter_id).order_by(Comment.created_at.desc())
    ).all()
    for comment in comments:
        _ = comment.user

    return templates.TemplateResponse("chapter_read.html", {
        "request": request, "chapter": chapter, "pages": pages,
        "comments": comments, "current_user": current_user,
        "comic_id": comic_id, "comic": comic,
        "prev_chapter": prev_chapter, "next_chapter": next_chapter,
        "title": f"{chapter.title} — ComixHub"
    })


# ── Добавление комментария ────────────────────────────────────────────────────

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


# ── Удаление комментария ──────────────────────────────────────────────────────

@router.post("/{comic_id}/chapters/{chapter_id}/comments/{comment_id}/delete")
async def delete_comment(
    comic_id: int, chapter_id: int, comment_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    comment = session.exec(select(Comment).where(Comment.id == comment_id)).first()
    if not comment:
        raise HTTPException(status_code=404)
    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    # Удалить может: сам автор комментария ИЛИ автор комикса
    if comment.user_id != current_user.id and (not comic or comic.author_id != current_user.id):
        raise HTTPException(status_code=403)
    session.delete(comment)
    session.commit()
    return RedirectResponse(url=f"/comics/{comic_id}/chapters/{chapter_id}/read", status_code=303)


# ── Закладки ──────────────────────────────────────────────────────────────────

@router.post("/{comic_id}/favorite")
async def toggle_favorite(
    comic_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    existing = session.exec(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.comic_id == comic_id
        )
    ).first()
    if existing:
        session.delete(existing)
    else:
        session.add(Favorite(user_id=current_user.id, comic_id=comic_id))
    session.commit()
    return RedirectResponse(url=f"/comics/{comic_id}", status_code=303)