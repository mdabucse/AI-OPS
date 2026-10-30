from fastapi import APIRouter, HTTPException, Query, Request

from app.auth import current_user
from app.rag import retrieve_context


router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/search")
def search_knowledge(
    request: Request,
    q: str = Query(min_length=1),
    top_k: int = Query(default=3, ge=1, le=10),
) -> dict:
    if current_user(request) is None:
        raise HTTPException(status_code=401, detail="Login required")
    return {"query": q, "results": retrieve_context(q, top_k=top_k)}
