"""
/api/v1/webhooks/telemetry  — Real-time prospect activity interceptor
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


class TelemetryPayload(BaseModel):
    company_id: str
    event: str  # "page_view" | "pricing_click"


@router.post("/telemetry")
async def receive_telemetry(payload: TelemetryPayload):
    print(
        f"\n\n"
        f"🚨🚨🚨 ABC GTM TELEMETRY ALERT: PROSPECT {payload.company_id} "
        f"JUST TRIGGERED {payload.event} 🚨🚨🚨"
        f"\n\n",
        flush=True,
    )
    return {"status": "received", "company_id": payload.company_id, "event": payload.event}
