from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select
from typing import Optional

from app.database import get_session
from app.models import Comic, User
from app.routers.auth import get_current_user
from app.templates import templates   # если templates вынесен, иначе импортируем ниже

router = APIRouter(prefix="/comics", tags=["comics"])


# ====================== Список комиксов ======================
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


# ====================== Форма создания комикса ======================
@router.get("/new", response_class=HTMLResponse)
async def new_comic_form(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(
            status_code=403, 
            detail="Только авторы могут публиковать комиксы. Пожалуйста, войдите как автор."
        )
    
    return templates.TemplateResponse("comic_form.html", {
        "request": request,
        "current_user": current_user
    })


# ====================== Создание комикса ======================
@router.post("/")
async def create_comic(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_author:
        raise HTTPException(status_code=403, detail="Только авторы могут публиковать комиксы")

    new_comic = Comic(
        title=title,
        description=description,
        author_id=current_user.id
    )
    
    session.add(new_comic)
    session.commit()
    session.refresh(new_comic)

    return RedirectResponse(url="/comics/", status_code=303)