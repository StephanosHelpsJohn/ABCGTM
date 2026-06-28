"""
/api/v1/competitor  — Competitor Trap: analyze a prospect reply mentioning a competitor
"""
from fastapi import APIRouter
from pydantic import BaseModel

from services import competitor_service

router = APIRouter(prefix="/api/v1/competitor", tags=["Competitor"])


class AnalyzeRequest(BaseModel):
    reply_text: str
    our_product: str = "Fetch AI"
    our_advantages: list[str] = []


@router.post("/analyze")
async def analyze(payload: AnalyzeRequest):
    result = await competitor_service.analyze_reply(
        payload.reply_text,
        payload.our_product,
        payload.our_advantages or None,
    )
    return result
