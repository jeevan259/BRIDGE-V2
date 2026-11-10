"""AI provider status endpoint."""
from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.ai.gemini import get_ai_status
from app.api.deps import bearer_scheme

router = APIRouter(prefix="/ai", tags=["ai"])


class AIStatusResponse(BaseModel):
    provider: str
    mode: str
    model: str
    last_error: str | None


@router.get("/status", response_model=AIStatusResponse)
async def ai_status(
    _creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> AIStatusResponse:
    return AIStatusResponse(**(await get_ai_status()))
