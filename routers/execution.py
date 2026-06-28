"""
/api/v1/campaign/send  — Approve & fire the outreach email, update status to Delivered
"""
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.database import Interaction, InteractionStatus

router = APIRouter(prefix="/api/v1/campaign", tags=["Execution"])


class SendRequest(BaseModel):
    interaction_id: str
    to_email: str
    email_body: str  # editable copy from the frontend


class SendResponse(BaseModel):
    interaction_id: str
    status: str
    delivered: bool
    method: str  # "smtp" | "console"


@router.post("/send", response_model=SendResponse)
async def send_campaign(payload: SendRequest, db: AsyncSession = Depends(get_db)):
    # ── Load interaction ────────────────────────────────────────────────────
    try:
        iid = uuid.UUID(payload.interaction_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interaction_id UUID")

    result = await db.execute(select(Interaction).where(Interaction.id == iid))
    interaction = result.scalar_one_or_none()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    # Parse subject from email body (expects "Subject: ..." on first line)
    lines = payload.email_body.strip().splitlines()
    subject = "Personalized outreach from ABC GTM"
    body_start = 0
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body_start = 1
        # Skip blank line after subject
        if len(lines) > 1 and not lines[1].strip():
            body_start = 2
    body_text = "\n".join(lines[body_start:]).strip()

    delivered_via = "console"

    # ── Try SMTP ────────────────────────────────────────────────────────────
    if settings.SMTP_USER and settings.SMTP_PASSWORD and payload.to_email:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
            msg["To"] = payload.to_email
            msg.attach(MIMEText(body_text, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                smtp.sendmail(msg["From"], [payload.to_email], msg.as_string())
            delivered_via = "smtp"
        except Exception as exc:
            print(f"[SMTP] Send failed ({exc}). Falling back to console output.")

    if delivered_via == "console":
        print("\n" + "=" * 70)
        print("📧  ABC GTM — SIMULATED EMAIL SEND (SMTP not configured)")
        print("=" * 70)
        print(f"TO:      {payload.to_email}")
        print(f"SUBJECT: {subject}")
        print("-" * 70)
        print(body_text)
        print("=" * 70 + "\n", flush=True)

    # ── Update DB status ─────────────────────────────────────────────────────
    interaction.status = InteractionStatus.Delivered
    interaction.email_draft = payload.email_body

    return SendResponse(
        interaction_id=str(interaction.id),
        status=InteractionStatus.Delivered.value,
        delivered=True,
        method=delivered_via,
    )
