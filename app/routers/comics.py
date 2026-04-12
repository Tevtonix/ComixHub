from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select
from typing import Optional, List
import shutil
from pathlib import Path
import uuid
import json

from app.database import get_session
from app.models import Comic, User, Chapter, Comment   # ← добавили Comment
from app.routers.auth import get_current_user

router = APIRouter(prefix="/comics", tags=["comics"])

UPLOAD_DIR_COVERS = Path("static/uploads/covers")
UPLOAD_DIR_CHAPTERS = Path("static/uploads/chapters")
UPLOAD_DIR_COVERS.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR_CHAPTERS.mkdir(parents=True, exist_ok=True)


# ====================== Список комиксов + Поиск ======================
@router.get("/", response_class=HTMLResponse)
async def list_comics(
    request: Request,
    q: Optional[str] = None,                    # параметр поиска
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
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "comics": comics,
            "current_user": current_user,
            "title": "Все комиксы",
            "search_query": q or ""
        }
    )


# ====================== Детальная страница комикса ======================
@router.get("/{comic_id}", response_class=HTMLResponse)
async def get_comic(
    comic_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    comic = session.exec(
        select(Comic).where(Comic.id == comic_id).join(User, Comic.author_id == User.id)
    ).first()
    
    if not comic:
        raise HTTPException(status_code=404, detail="Комикс не найден")

    return templates.TemplateResponse("comic_detail.html", {
        "request": request,
        "comic": comic,
        "current_user": current_user,
        "title": comic.title
    })


# ====================== Форма создания главы ======================
@router.get("/{comic_id}/chapters/new", response_class=HTMLResponse)
async def new_chapter_form(
    comic_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403, detail="Только авторы могут добавлять главы")

    comic = session.exec(select(Comic).where(Comic.id == comic_id)).first()
    if not comic or comic.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы можете добавлять главы только к своим комиксам")

    return templates.TemplateResponse("chapter_form.html", {
        "request": request,
        "comic": comic,
        "current_user": current_user
    })


# ====================== Создание главы ======================
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
            ext = page.filename.split(".")[-1].lower()
            filename = f"{uuid.uuid4()}.{ext}"
            file_path = chapter_dir / filename

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(page.file, buffer)

            page_paths.append(f"/static/uploads/chapters/{comic_id}/{chapter_number}/{filename}")

    new_chapter = Chapter(
        comic_id=comic_id,
        chapter_number=chapter_number,
        title=title,
        pages=json.dumps(page_paths)
    )

    session.add(new_chapter)
    session.commit()

    return RedirectResponse(url=f"/comics/{comic_id}", status_code=303)


# ====================== Чтение главы + комментарии ======================
@router.get("/{comic_id}/chapters/{chapter_id}/read", response_class=HTMLResponse)
async def read_chapter(
    comic_id: int,
    chapter_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    chapter = session.exec(select(Chapter).where(Chapter.id == chapter_id)).first()

    if not chapter or chapter.comic_id != comic_id:
        raise HTTPException(status_code=404, detail="Глава не найдена")

    pages = chapter.get_pages()

    # Загружаем комментарии
    comments = session.exec(
        select(Comment)
        .where(Comment.chapter_id == chapter_id)
        .order_by(Comment.created_at.desc())
    ).all()

    return templates.TemplateResponse("chapter_read.html", {
        "request": request,
        "chapter": chapter,
        "pages": pages,
        "comments": comments,
        "current_user": current_user,
        "comic_id": comic_id,
        "title": f"{chapter.title} — ComixHub"
    })


# ====================== Добавление комментария ======================
@router.post("/{comic_id}/chapters/{chapter_id}/comment")
async def add_comment(
    comic_id: int,
    chapter_id: int,
    text: str = Form(...),
    rating: Optional[int] = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Необходимо войти в аккаунт")

    comment = Comment(
        chapter_id=chapter_id,
        user_id=current_user.id,
        text=text,
        rating=rating
    )

    session.add(comment)
    session.commit()

    return RedirectResponse(
        url=f"/comics/{comic_id}/chapters/{chapter_id}/read", 
        status_code=303
    )

# ====================== Закладки ======================

@router.post("/{comic_id}/favorite")
async def toggle_favorite(
    comic_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Необходимо войти в аккаунт")

    # Проверяем, есть ли уже закладка
    existing = session.exec(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.comic_id == comic_id
        )
    ).first()

    if existing:
        # Удаляем из закладок
        session.delete(existing)
        session.commit()
        action = "removed"
    else:
        # Добавляем в закладки
        favorite = Favorite(user_id=current_user.id, comic_id=comic_id)
        session.add(favorite)
        session.commit()
        action = "added"

    return RedirectResponse(url=f"/comics/{comic_id}", status_code=303)


# Страница "Мои закладки"
@router.get("/favorites", response_class=HTMLResponse)
async def my_favorites(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Необходимо войти в аккаунт")

    favorites = session.exec(
        select(Comic)
        .join(Favorite, Comic.id == Favorite.comic_id)
        .where(Favorite.user_id == current_user.id)
    ).all()

    return templates.TemplateResponse("favorites.html", {
        "request": request,
        "comics": favorites,
        "current_user": current_user,
        "title": "Мои закладки"
    })