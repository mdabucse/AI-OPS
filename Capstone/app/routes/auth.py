from time import perf_counter, sleep

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import SessionLocal
from app.pool_state import BASELINE_POOL_SIZE, get_pool_size


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    started_at = perf_counter()
    if username != settings.demo_username or password != settings.demo_password:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid demo credentials.", "login_duration_ms": duration_ms},
            status_code=401,
        )
    with SessionLocal() as session:
        pool_size = get_pool_size(session)
    # The baseline training state is intentionally saturated so the first
    # successful login visibly demonstrates the latency problem.
    if pool_size <= BASELINE_POOL_SIZE:
        sleep(1.2)
    request.session["username"] = username
    request.session["login_duration_ms"] = round((perf_counter() - started_at) * 1000, 2)
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
