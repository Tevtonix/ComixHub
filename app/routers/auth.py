from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_session
from app.models import User
from app.schemas import UserCreate, TokenData
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
templates = Jinja2Templates(directory="app/templates")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    request: Request, 
    session: Session = Depends(get_session)
) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    user = session.exec(select(User).where(User.username == username)).first()
    return user



@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})



@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    is_author: bool = Form(False),
    session: Session = Depends(get_session)
):
    existing_user = session.exec(select(User).where(User.username == username)).first()
    if existing_user:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Имя пользователя уже занято"}
        )

    hashed_password = get_password_hash(password)
    
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_author=is_author
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return RedirectResponse(url="/auth/login", status_code=303)



@router.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == username)).first()
    
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse(url="/auth/login?error=invalid", status_code=303)

    access_token = create_access_token(data={"sub": user.username})

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,   # 7 дней
        samesite="lax"
    )

    return RedirectResponse(url="/", status_code=303)