from fastapi import FastAPI, Request, Depends
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel

from app.database import engine
from app.routers import comics, auth
from app.routers.auth import get_current_user

app = FastAPI(title="ComixHub")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

SQLModel.metadata.create_all(bind=engine)

app.include_router(comics.router)
app.include_router(auth.router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Главная",
            "current_user": current_user
        }
    )