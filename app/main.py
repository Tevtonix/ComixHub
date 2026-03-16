from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import engine, SQLModel
from app.models import Comic
from app.routers import comics

app = FastAPI(title="ComixHub — Alpha")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

SQLModel.metadata.create_all(engine)

app.include_router(comics.router, prefix="/comics", tags=["comics"])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "title": "ComixHub — главная"}
    )