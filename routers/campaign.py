"""
/api/v1/campaign/generate  — Run full ABC GTM pipeline for a target domain
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.database import Company, Interaction, InteractionStatus
from services import agent_service

router = APIRouter(prefix="/api/v1/campaign", tags=["Campaign"])


class GenerateRequest(BaseModel):
    domain: str
    persona: str = "VP Sales"


class GenerateResponse(BaseModel):
    company_id: str
    interaction_id: str
    company_name: Optional[str]
    email_draft: str
    microsite_url: str
    full_microsite_url: str


@router.post("/generate", response_model=GenerateResponse)
async def generate_campaign(payload: GenerateRequest, db: AsyncSession = Depends(get_db)):
    domain = payload.domain.lower().strip().removeprefix("https://").removeprefix("http://").rstrip("/")

    # ── 1. Enrich via Orange Slice ─────────────────────────────────────────────
    enriched = await agent_service.enrich_target(domain, payload.persona)
    company_name = enriched.get("company_name", domain.split(".")[0].capitalize())

    # ── 2. Upsert Company ──────────────────────────────────────────────────────
    result = await db.execute(select(Company).where(Company.domain == domain))
    company = result.scalar_one_or_none()

    if company is None:
        company = Company(domain=domain, name=company_name, enriched_data=enriched)
        db.add(company)
        await db.flush()
    else:
        company.name = company_name
        company.enriched_data = enriched

    # ── 3. Draft Email ─────────────────────────────────────────────────────────
    email_draft = await agent_service.draft_outreach(enriched)

    # ── 4. Generate Microsite ──────────────────────────────────────────────────
    microsite_path = await agent_service.generate_microsite(enriched, str(company.id))

    # ── 5. Save Interaction ────────────────────────────────────────────────────
    full_url = f"{settings.BASE_URL}{microsite_path}"
    interaction = Interaction(
        company_id=company.id,
        status=InteractionStatus.Drafted,
        email_draft=email_draft,
        microsite_url=full_url,
    )
    db.add(interaction)
    await db.flush()

    return GenerateResponse(
        company_id=str(company.id),
        interaction_id=str(interaction.id),
        company_name=company_name,
        email_draft=email_draft,
        microsite_url=microsite_path,
        full_microsite_url=full_url,
    )
