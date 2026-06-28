"""
/api/v1/decks  — Generate branded HTML microsites from a company URL
"""
from fastapi import APIRouter
from pydantic import BaseModel

from services import deck_service

router = APIRouter(prefix="/api/v1/decks", tags=["Decks"])


class DeckRequest(BaseModel):
    url: str
    pitch: str = ""


@router.post("/generate")
async def generate_deck(payload: DeckRequest):
    url = payload.url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    result = await deck_service.generate_deck(url, payload.pitch)
    return result
