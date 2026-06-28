"""
Fetch AI — Event Listener Service
Scans for buy signals (news, job postings) and drafts event-triggered emails.
"""
import asyncio
import json
import textwrap
from pathlib import Path

from openai import AsyncOpenAI

from core.config import settings

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"

_openai = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY or "no-key",
    base_url="https://api.openai.com/v1",
)
_HAS_OPENAI = bool(
    settings.OPENAI_API_KEY
    and settings.OPENAI_API_KEY not in ("", "no-key", "ollama")
)


async def scan_signals(domain: str, keywords: list[str], persona: str) -> dict:
    """Run Orange Slice event scan and return signals + triggered email drafts."""
    script = SCRIPTS_DIR / "scan_events.mjs"
    kw_str = ",".join(keywords) if keywords else ""

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", str(script), domain, kw_str,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(SCRIPTS_DIR.parent),
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        scan_data = json.loads(stdout.decode())
    except Exception as exc:
        print(f"[EventService] scan failed ({exc}). Using demo data.")
        scan_data = _demo_scan(domain, keywords)

    # Draft emails for the top 3 most relevant signals
    signals = scan_data.get("news_events", []) + scan_data.get("job_openings", [])
    triggered = []

    for sig in signals[:3]:
        trigger_text = sig.get("summary") or sig.get("title") or "company activity"
        email = await _draft_triggered_email(
            company_name=scan_data.get("company_name", domain),
            domain=domain,
            industry=scan_data.get("industry", "B2B"),
            persona=persona,
            trigger_event=trigger_text,
            event_type=sig.get("type", "news"),
        )
        triggered.append({
            "signal": sig,
            "email_draft": email,
        })

    return {
        "domain": domain,
        "company_name": scan_data.get("company_name"),
        "total_signals": scan_data.get("total_signals", len(signals)),
        "triggered": triggered,
    }


async def _draft_triggered_email(
    company_name: str,
    domain: str,
    industry: str,
    persona: str,
    trigger_event: str,
    event_type: str,
) -> str:
    if not _HAS_OPENAI:
        return _demo_email(company_name, persona, trigger_event)

    system = textwrap.dedent("""
        You are an expert B2B cold email writer. You write short, hyper-relevant emails
        that reference a *specific* recent event at the prospect's company.
        Rules:
        - Subject line MUST reference the specific event
        - Opening line proves you saw the news — quote or paraphrase it
        - Connect the event to a pain point or opportunity
        - Single clear CTA (15-min call or quick reply)
        - Under 120 words in the body
        Output ONLY: Subject: ... then blank line then body. No preamble.
    """).strip()

    user = textwrap.dedent(f"""
        Write a triggered cold email referencing this specific event:

        Company: {company_name} ({domain})
        Industry: {industry}
        Target persona: {persona}
        Event type: {event_type}
        Event: "{trigger_event}"

        Our product: Fetch AI — AI-powered sales automation. We help {persona}s
        cut outreach cycles from days to seconds using real-time signal data and
        GPT-4o personalization.

        The email should open by referencing exactly "{trigger_event}" and pivot
        to how Fetch AI can help them capitalize on this moment.
    """).strip()

    try:
        resp = await _openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.65,
            max_tokens=350,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        print(f"[EventService] draft failed: {exc}")
        return _demo_email(company_name, persona, trigger_event)


def _demo_email(company_name: str, persona: str, trigger: str) -> str:
    return (
        f"Subject: Re: {company_name}'s recent move — quick question\n\n"
        f"Hi [First Name],\n\n"
        f"Saw that {trigger.rstrip('.')} — that's a big moment.\n\n"
        f"When companies hit this inflection point, the outreach team usually gets "
        f"buried. Fetch AI auto-identifies warm signals like this one, generates a "
        f"personalized microsite per prospect, and fires tailored emails in under 10 seconds.\n\n"
        f"Worth a 15-min look? I can show you how it works for {company_name} specifically.\n\n"
        f"[Your Name]"
    )


def _demo_scan(domain: str, keywords: list[str]) -> dict:
    company = domain.split(".")[0].capitalize()
    return {
        "domain": domain,
        "company_name": company,
        "industry": "B2B SaaS",
        "employee_count": 350,
        "total_signals": 3,
        "news_events": [
            {
                "type": "news",
                "category": "receives_financing",
                "summary": f"{company} raised a $30M Series B led by Andreessen Horowitz to expand its sales platform.",
                "date": "2026-05-15",
                "url": None,
            },
            {
                "type": "news",
                "category": "hires",
                "summary": f"{company} hired Sarah Chen as VP of Revenue Operations to scale the GTM team.",
                "date": "2026-05-20",
                "url": None,
            },
        ],
        "job_openings": [
            {
                "type": "job",
                "category": "sales",
                "title": "Senior Account Executive — Enterprise",
                "location": "San Francisco, CA",
                "url": None,
                "date": "2026-06-01",
            },
        ],
    }
