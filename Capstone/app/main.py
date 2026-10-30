from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routes.simulation import router as simulation_router
from app.routes.approvals import router as approvals_router
from app.routes.auth import router as auth_router
from app.routes.ui import router as ui_router
from app.routes.rag import router as rag_router
from app.routes.alerts import router as alerts_router
from app.routes.governance import router as governance_router


app = FastAPI(title="AIOps Capstone RCA Agent")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(simulation_router)
app.include_router(approvals_router)
app.include_router(auth_router)
app.include_router(ui_router)
app.include_router(rag_router)
app.include_router(alerts_router)
app.include_router(governance_router)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
