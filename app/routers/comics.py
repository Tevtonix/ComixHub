from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import select, Session

from app.database import get_session
from app.models import Comic
from app.schemas import ComicCreate, ComicRead

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def list_comics(request: Request, session: Session = Depends(get_session)):
    comics = session.exec(select(Comic)).all()
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "comics": comics}
    )

@router.get("/new", response_class=HTMLResponse)
async def new_comic_form(request: Request):
    return templates.TemplateResponse("comic_form.html", {"request": request})

@router.post("/", response_class=RedirectResponse)
async def create_comic(
    title: str = Form(...),
    description: str = Form(None),
    session: Session = Depends(get_session)
):
    comic = Comic(title=title, description=description)
    session.add(comic)
    session.commit()
    session.refresh(comic)
    return RedirectResponse("/comics/", status_code=303)