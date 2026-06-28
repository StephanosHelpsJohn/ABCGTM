"""
Fetch AI — Competitor Trap Service
Analyzes a prospect reply mentioning a competitor, identifies the competitor,
and drafts a targeted response with specific advantages + a comparison table.
"""
import textwrap

from openai import AsyncOpenAI

from core.config import settings

_openai = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY or "no-key",
    base_url="https://api.openai.com/v1",
)
_HAS_OPENAI = bool(
    settings.OPENAI_API_KEY
    and settings.OPENAI_API_KEY not in ("", "no-key", "ollama")
)


async def analyze_reply(
    reply_text: str,
    our_product: str = "Fetch AI",
    our_advantages: list[str] | None = None,
) -> dict:
    """
    Parse a prospect reply, identify the competitor, and return:
    - competitor name
    - detected objection
    - draft response
    - HTML comparison table
    """
    if not _HAS_OPENAI:
        return _demo_analysis(reply_text, our_product)

    advantages_str = "\n".join(f"- {a}" for a in (our_advantages or []))

    system = textwrap.dedent("""
        You are an elite B2B sales strategist. When a prospect mentions a competitor,
        your job is to:
        1. Identify the competitor mentioned
        2. Understand the underlying objection
        3. Draft a warm, confident, non-defensive reply that:
           - Validates their choice ("Smart choice using X — they're solid")
           - Pivots to 2-3 specific advantages we have over that competitor
           - Includes a dynamic HTML comparison table (inline CSS, dark theme, 3+ rows)
           - Ends with a soft CTA
        Output VALID JSON with exactly these keys:
        {
          "competitor": "<name>",
          "objection": "<one-sentence summary>",
          "reply": "<full email reply as plain text with \\n newlines>",
          "comparison_html": "<self-contained HTML table with inline CSS>"
        }
        No markdown fences. Pure JSON.
    """).strip()

    user = textwrap.dedent(f"""
        Prospect reply to analyze:
        ---
        {reply_text}
        ---

        Our product: {our_product}
        Our key advantages (if any provided):
        {advantages_str or "Faster setup, better AI personalization, event-triggered outreach, real-time telemetry."}

        Generate the JSON analysis.
    """).strip()

    try:
        resp = await _openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.6,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        import json
        result = json.loads(resp.choices[0].message.content)
        # Ensure all keys present
        result.setdefault("competitor", "Unknown")
        result.setdefault("objection", "Prospect is using a competitor")
        result.setdefault("reply", _demo_analysis(reply_text, our_product)["reply"])
        result.setdefault("comparison_html", _demo_table(result["competitor"], our_product))
        return result
    except Exception as exc:
        print(f"[CompetitorService] analysis failed: {exc}")
        return _demo_analysis(reply_text, our_product)


def _demo_analysis(reply_text: str, our_product: str) -> dict:
    # Try to detect common competitors
    competitors = {
        "outreach": "Outreach.io",
        "salesloft": "Salesloft",
        "hubspot": "HubSpot",
        "salesforce": "Salesforce",
        "apollo": "Apollo.io",
        "zoominfo": "ZoomInfo",
        "clay": "Clay",
        "lemlist": "Lemlist",
        "instantly": "Instantly.ai",
        "smartreach": "SmartReach",
    }
    reply_lower = reply_text.lower()
    detected = next(
        (name for key, name in competitors.items() if key in reply_lower),
        "your current solution"
    )

    reply = (
        f"Hey [First Name],\n\n"
        f"Thanks for the context — {detected} is solid, totally get it.\n\n"
        f"A few teams we've brought over from {detected} made the switch because "
        f"{our_product} does three things differently: event-triggered outreach "
        f"(we fire emails the moment a prospect raises funding or posts a key role), "
        f"per-prospect branded microsites that track opens in real time, and a setup "
        f"time of under 30 minutes vs the typical 2-week {detected} implementation.\n\n"
        f"Would it make sense to do a quick 15-min comparison? I'll show you exactly "
        f"what's different side-by-side — no sales pitch, just the facts.\n\n"
        f"[Your Name]"
    )

    return {
        "competitor": detected,
        "objection": f"Prospect is currently using {detected}",
        "reply": reply,
        "comparison_html": _demo_table(detected, our_product),
    }


def _demo_table(competitor: str, our_product: str) -> str:
    rows = [
        ("Setup time", "30 minutes", "2+ weeks"),
        ("Event-triggered outreach", "✓ Real-time signals", "✗ Manual"),
        ("Per-prospect microsites", "✓ Auto-generated", "✗ Not available"),
        ("Live open tracking", "✓ Instant alerts", "~ Limited"),
        ("AI email personalization", "✓ GPT-4o per signal", "~ Template-based"),
        ("Price", "Usage-based, no seat fees", "Per-seat licensing"),
    ]
    rows_html = "\n".join(
        f"""<tr>
          <td style="padding:10px 16px;border-bottom:1px solid rgba(255,255,255,.07);color:rgba(255,255,255,.6)">{r}</td>
          <td style="padding:10px 16px;border-bottom:1px solid rgba(255,255,255,.07);color:#4ade80;font-weight:600">{u}</td>
          <td style="padding:10px 16px;border-bottom:1px solid rgba(255,255,255,.07);color:rgba(255,255,255,.35)">{c}</td>
        </tr>"""
        for r, u, c in rows
    )
    return f"""<table style="width:100%;border-collapse:collapse;background:#111;border-radius:12px;overflow:hidden;font-family:system-ui,sans-serif;font-size:13px">
  <thead>
    <tr style="background:rgba(255,255,255,.05)">
      <th style="padding:12px 16px;text-align:left;color:rgba(255,255,255,.4);font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.06em">Feature</th>
      <th style="padding:12px 16px;text-align:left;color:#F5A623;font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.06em">{our_product}</th>
      <th style="padding:12px 16px;text-align:left;color:rgba(255,255,255,.4);font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.06em">{competitor}</th>
    </tr>
  </thead>
  <tbody>
{rows_html}
  </tbody>
</table>"""
