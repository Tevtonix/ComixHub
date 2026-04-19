from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, Comic, Comment, Favorite
from app.routers.auth import get_current_user
from typing import Optional

router = APIRouter(prefix="/profile", tags=["profile"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/me", response_class=HTMLResponse)
async def my_profile(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return RedirectResponse(url=f"/profile/{current_user.id}", status_code=303)


@router.get("/{user_id}", response_class=HTMLResponse)
async def view_profile(
    user_id: int, request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    profile_user = session.exec(select(User).where(User.id == user_id)).first()
    if not profile_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    comics = []
    if profile_user.is_author:
        comics = session.exec(
            select(Comic).where(Comic.author_id == user_id).order_by(Comic.created_at.desc())
        ).all()

    favorites = []
    is_own_profile = current_user and current_user.id == user_id
    if is_own_profile:
        favorites = session.exec(
            select(Comic)
            .join(Favorite, Comic.id == Favorite.comic_id)
            .where(Favorite.user_id == user_id)
        ).all()

    comments = session.exec(
        select(Comment).where(Comment.user_id == user_id).order_by(Comment.created_at.desc()).limit(10)
    ).all()
    for c in comments:
        _ = c.chapter  # lazy load

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "profile_user": profile_user,
        "comics": comics,
        "favorites": favorites,
        "comments": comments,
        "is_own_profile": is_own_profile,
        "current_user": current_user,
        "title": f"Профиль: {profile_user.username}"
    })


@router.get("/me/edit", response_class=HTMLResponse)
async def edit_profile_form(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse("profile_edit.html", {
        "request": request,
        "current_user": current_user,
        "title": "Редактировать профиль"
    })


@router.post("/me/edit")
async def edit_profile(
    request: Request,
    email: str = Form(...),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    existing = session.exec(
        select(User).where(User.email == email, User.id != current_user.id)
    ).first()
    if existing:
        return templates.TemplateResponse("profile_edit.html", {
            "request": request,
            "current_user": current_user,
            "error": "Этот email уже используется",
            "title": "Редактировать профиль"
        })

    current_user.email = email
    session.add(current_user)
    session.commit()
    return RedirectResponse(url=f"/profile/{current_user.id}", status_code=303)