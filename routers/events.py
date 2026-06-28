"""
/api/v1/events  — Buy signal scanner + event-triggered email generation
"""
from fastapi import APIRouter
from pydantic import BaseModel

from services import event_service

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


class ScanRequest(BaseModel):
    domain: str
    keywords: list[str] = []
    persona: str = "VP Sales"


@router.post("/scan")
async def scan_events(payload: ScanRequest):
    domain = (
        payload.domain.lower().strip()
        .removeprefix("https://")
        .removeprefix("http://")
        .rstrip("/")
    )
    result = await event_service.scan_signals(domain, payload.keywords, payload.persona)
    return result
