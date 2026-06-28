"""
/api/v1/crm  — Contacts & company CRM view
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.database import Company, Interaction

router = APIRouter(prefix="/api/v1/crm", tags=["CRM"])


@router.get("/contacts")
async def list_contacts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).order_by(Company.created_at.desc()))
    companies = result.scalars().all()

    rows = []
    for co in companies:
        latest = max(co.interactions, key=lambda i: i.created_at, default=None)
        rows.append({
            "id": str(co.id),
            "domain": co.domain,
            "name": co.name,
            "industry": (co.enriched_data or {}).get("industry"),
            "employee_count": (co.enriched_data or {}).get("employee_count"),
            "hq": (co.enriched_data or {}).get("hq"),
            "latest_round": (co.enriched_data or {}).get("latest_round"),
            "tech_stack": (co.enriched_data or {}).get("tech_stack", [])[:5],
            "status": latest.status.value if latest else "—",
            "microsite_url": latest.microsite_url if latest else None,
            "created_at": co.created_at.isoformat(),
        })

    return {"contacts": rows, "total": len(rows)}


@router.delete("/contacts/{company_id}", status_code=204)
async def delete_contact(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.domain == company_id))
    co = result.scalar_one_or_none()
    if co:
        await db.delete(co)
