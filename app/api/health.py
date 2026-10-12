from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import __version__

router = APIRouter(prefix="/health", tags=["health"])


class LiveResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str


@router.get("/live", response_model=LiveResponse)
async def live(request: Request) -> LiveResponse:
    return LiveResponse(
        status="ok", service=request.app.state.settings.app_name, version=__version__
    )
