"""AI provider status endpoint."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.gemini import get_ai_status
from app.api.deps import CurrentUser

router = APIRouter(prefix="/ai", tags=["ai"])


class AIStatusResponse(BaseModel):
    provider: str
    mode: str
    model: str
    last_error: str | None


@router.get("/status", response_model=AIStatusResponse)
async def ai_status(_: CurrentUser) -> AIStatusResponse:
    return AIStatusResponse(**(await get_ai_status()))
