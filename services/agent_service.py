"""
ABC GTM — Agent Service
Pipeline: Orange Slice Enrichment → OpenAI Draft → Microsite Generation
"""
import json
import textwrap
from pathlib import Path

import httpx
from openai import AsyncOpenAI

from core.config import settings

STATIC_DIR = Path(__file__).parent.parent / "static"
MICROSITES_DIR = STATIC_DIR / "microsites"
MICROSITES_DIR.mkdir(parents=True, exist_ok=True)

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# ── Orange Slice Enrichment ────────────────────────────────────────────────────

async def enrich_target(domain: str, persona: str) -> dict:
    """
    Calls the Orange Slice AI waterfall enrichment API.
    Returns firmographics, recent news, and intent signals.
    Falls back to a structured mock if the API is unreachable (for demo safety).
    """
    headers = {
        "Authorization": f"Bearer {settings.ORANGE_SLICE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"domain": domain, "persona": persona, "waterfall": True}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{settings.ORANGE_SLICE_BASE_URL}/enrich",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data
    except Exception as exc:
        print(f"[Orange Slice] Enrichment API unreachable ({exc}). Using structured fallback for demo.")
        return _demo_enrichment(domain, persona)


def _demo_enrichment(domain: str, persona: str) -> dict:
    """Structured fallback enrichment data for demo / offline use."""
    company_name = domain.split(".")[0].capitalize()
    return {
        "domain": domain,
        "company_name": company_name,
        "industry": "B2B SaaS",
        "employee_count": "200-500",
        "annual_revenue": "$20M-$50M",
        "hq": "San Francisco, CA",
        "tech_stack": ["Salesforce", "HubSpot", "Slack", "AWS"],
        "recent_news": [
            f"{company_name} announced a Series B funding round of $25M to accelerate growth.",
            f"{company_name} is actively hiring across sales and engineering.",
        ],
        "intent_signals": [
            "High research activity on 'sales automation' and 'pipeline velocity'",
            "Multiple visits to competitor pricing pages in the last 30 days",
            f"Target persona '{persona}' is active on LinkedIn, posting about revenue ops",
        ],
        "target_persona": persona,
    }


# ── OpenAI Email Drafter ───────────────────────────────────────────────────────

async def draft_outreach(enriched_data: dict) -> str:
    """Uses GPT-4o to write a hyper-personalized cold email from enrichment data."""
    system_prompt = textwrap.dedent("""
        You are an elite B2B cold email copywriter. You write concise, insight-driven emails
        that feel personally researched — not templated. Your emails have:
        - A subject line that references a specific signal or trigger
        - An opening that proves you did your homework (reference news, hiring, intent)
        - A single clear value proposition tied to their pain
        - A low-friction CTA (reply, 15-min call, or click a link)
        - Under 150 words in the body
        Output ONLY the email content (Subject: ... then body). No preamble.
    """).strip()

    user_prompt = textwrap.dedent(f"""
        Write a cold outreach email for the following prospect:

        Company: {enriched_data.get('company_name', enriched_data.get('domain'))}
        Domain: {enriched_data.get('domain')}
        Industry: {enriched_data.get('industry', 'Unknown')}
        Revenue: {enriched_data.get('annual_revenue', 'Unknown')}
        Tech Stack: {', '.join(enriched_data.get('tech_stack', []))}
        Target Persona: {enriched_data.get('target_persona', 'VP Sales')}
        Recent News: {json.dumps(enriched_data.get('recent_news', []))}
        Intent Signals: {json.dumps(enriched_data.get('intent_signals', []))}

        Our product: ABC GTM — an AI-powered sales automation platform that identifies
        high-intent prospects, auto-generates personalized microsites, and fires
        outreach at the perfect moment. We help revenue teams cut their outreach
        cycle from days to minutes.
    """).strip()

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


# ── Microsite Generator ────────────────────────────────────────────────────────

async def generate_microsite(enriched_data: dict, company_id: str) -> str:
    """
    Prompts GPT-4o to output a complete single-file HTML microsite tailored to the prospect.
    Injects telemetry JS, saves to static/microsites/{company_id}.html.
    Returns the file URL path.
    """
    company_name = enriched_data.get("company_name", enriched_data.get("domain", "Your Company"))
    persona = enriched_data.get("target_persona", "Sales Leader")

    telemetry_script = textwrap.dedent(f"""
    <script>
      (function() {{
        var cid = "{company_id}";
        var base = window.location.origin;
        function ping(event) {{
          fetch(base + "/api/v1/webhooks/telemetry", {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{company_id: cid, event: event}})
          }}).catch(function(){{}});
        }}
        ping("page_view");
        document.addEventListener("DOMContentLoaded", function() {{
          var btn = document.getElementById("pricing");
          if (btn) btn.addEventListener("click", function() {{ ping("pricing_click"); }});
        }});
      }})();
    </script>
    """).strip()

    system_prompt = textwrap.dedent("""
        You are a senior front-end designer. Output ONLY a complete, valid, single-file HTML document.
        No markdown. No code fences. No explanation. Just raw HTML starting with <!DOCTYPE html>.

        Design rules (follow strictly):
        1. Dark, modern aesthetic. Use inline CSS only (no external CDNs — they may be blocked).
        2. Main content must be centered with max-width: 680px and mx-auto padding — NOT left-aligned.
        3. Hero section: include a brand logo placeholder area. Behind the logo placeholder,
           render a solid red (#FF0034) rectangular box (e.g., 120x60px) as a fixed visual accent.
        4. DO NOT include any "X" shapes, cross marks, close-button icons, or ✕ characters anywhere.
        5. Include exactly one button with id="pricing" that says "See Pricing".
        6. Include a compelling hero headline, a value proposition paragraph, a 3-column feature grid,
           a social proof / stats bar, and a final CTA section.
        7. The page must look polished and real — as if a designer spent a day on it.
        8. The last tag before </body> will be injected externally — leave </body></html> at the very end.
    """).strip()

    user_prompt = textwrap.dedent(f"""
        Generate a personalized sales microsite for this prospect:

        Company: {company_name}
        Industry: {enriched_data.get('industry', 'B2B SaaS')}
        Employee Count: {enriched_data.get('employee_count', '200-500')}
        Revenue: {enriched_data.get('annual_revenue', 'Unknown')}
        HQ: {enriched_data.get('hq', 'Unknown')}
        Tech Stack: {', '.join(enriched_data.get('tech_stack', []))}
        Target Persona: {persona}
        Intent Signals: {json.dumps(enriched_data.get('intent_signals', []))}
        Recent News: {json.dumps(enriched_data.get('recent_news', []))}

        The microsite is from ABC GTM (AI-powered sales automation).
        Tailor every section — headline, features, proof points — specifically to {company_name}
        and the pain points a {persona} would care about given their signals above.
    """).strip()

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
        max_tokens=3000,
    )

    html_content = response.choices[0].message.content.strip()

    # Strip any accidental markdown fences
    if html_content.startswith("```"):
        html_content = html_content.split("```", 2)[-1].lstrip("html").lstrip("\n")
        if html_content.endswith("```"):
            html_content = html_content[: html_content.rfind("```")]

    # Inject telemetry before </body>
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", f"\n{telemetry_script}\n</body>")
    else:
        html_content += f"\n{telemetry_script}\n</body>\n</html>"

    # Save to disk
    output_path = MICROSITES_DIR / f"{company_id}.html"
    output_path.write_text(html_content, encoding="utf-8")

    return f"/static/microsites/{company_id}.html"
