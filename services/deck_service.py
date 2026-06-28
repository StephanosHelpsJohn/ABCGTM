"""
Fetch AI — Generate Decks Service
Reads a company website, extracts brand voice + visual identity,
and generates an HTML microsite in that style.
"""
import re
import textwrap
import uuid
from pathlib import Path

import httpx
from openai import AsyncOpenAI

from core.config import settings

STATIC_DIR = Path(__file__).parent.parent / "static"
DECKS_DIR  = STATIC_DIR / "decks"
DECKS_DIR.mkdir(parents=True, exist_ok=True)

_openai = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY or "no-key",
    base_url="https://api.openai.com/v1",
)
_HAS_OPENAI = bool(
    settings.OPENAI_API_KEY
    and settings.OPENAI_API_KEY not in ("", "no-key", "ollama")
)


async def generate_deck(url: str, pitch: str = "") -> dict:
    """Fetch the URL, extract brand signal, generate a matching microsite."""
    # ── 1. Fetch source HTML ──────────────────────────────────────────────────
    raw_html = ""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "FetchAI/1.0"})
            raw_html = resp.text[:20_000]  # cap at 20k chars
    except Exception as exc:
        print(f"[DeckService] fetch failed ({exc}). Proceeding with minimal context.")

    brand = _extract_brand_signals(raw_html, url)

    # ── 2. Generate microsite via GPT-4o ─────────────────────────────────────
    deck_id   = str(uuid.uuid4()).replace("-", "")[:12]
    html_path = await _generate_microsite(brand, pitch, deck_id)

    return {
        "deck_id": deck_id,
        "brand": brand,
        "microsite_url": f"/static/decks/{deck_id}.html",
        "full_url": f"{settings.BASE_URL}/static/decks/{deck_id}.html",
    }


def _extract_brand_signals(html: str, url: str) -> dict:
    """Pull colors, fonts, company name, and tone from raw HTML."""
    # Company name: from <title> or og:site_name
    name = ""
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        name = m.group(1).split("|")[0].split("–")[0].split("-")[0].strip()
    if not name:
        m = re.search(r'og:site_name["\s]+content=["\']([^"\']+)', html, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
    if not name:
        domain = re.sub(r"https?://", "", url).split("/")[0].replace("www.", "")
        name = domain.split(".")[0].capitalize()

    # Colors: find hex values mentioned in inline styles / CSS
    hex_colors = list(dict.fromkeys(re.findall(r"#([0-9a-fA-F]{6})\b", html)))[:8]
    colors = [f"#{c}" for c in hex_colors] if hex_colors else []

    # Font families
    fonts = list(dict.fromkeys(re.findall(r"font-family:\s*['\"]?([A-Za-z][A-Za-z\s]+?)['\";\s,]", html)))[:3]

    # Tagline: og:description or meta description
    tagline = ""
    m = re.search(r'(?:og:description|name=["\']description["\'])[^>]+content=["\']([^"\']{10,160})', html, re.IGNORECASE)
    if m:
        tagline = m.group(1).strip()

    # Tone keywords from h1/h2 tags
    headlines = re.findall(r"<h[12][^>]*>([^<]{5,80})</h[12]>", html, re.IGNORECASE)[:5]

    return {
        "company_name": name,
        "url": url,
        "colors": colors,
        "fonts": fonts,
        "tagline": tagline,
        "sample_headlines": headlines,
    }


async def _generate_microsite(brand: dict, pitch: str, deck_id: str) -> str:
    company  = brand["company_name"]
    tagline  = brand.get("tagline", "")
    colors   = brand.get("colors", [])
    fonts    = brand.get("fonts", [])
    heads    = brand.get("sample_headlines", [])

    if not _HAS_OPENAI:
        html = _demo_deck(brand, deck_id)
        (DECKS_DIR / f"{deck_id}.html").write_text(html, encoding="utf-8")
        return f"/static/decks/{deck_id}.html"

    system = textwrap.dedent("""
        You are a senior front-end designer creating a sales deck / microsite.
        Output ONLY a complete, valid single-file HTML document — no markdown fences,
        no explanation, just raw HTML starting with <!DOCTYPE html>.

        Design rules:
        1. Match the brand identity you're given (colors, fonts, tone).
        2. Dark or light theme based on the brand — infer from their color palette.
        3. Inline CSS only.
        4. Structure: Hero → Value Props (3 columns) → Social Proof → CTA.
        5. One primary CTA button with id="cta".
        6. End with </body></html>.
        7. Polished, production-ready. No placeholder text.
    """).strip()

    user = textwrap.dedent(f"""
        Create a sales microsite for this company:

        Company: {company}
        Source URL: {brand['url']}
        Tagline / description: {tagline or "N/A"}
        Brand colors found on site: {", ".join(colors[:5]) or "not detected"}
        Fonts found: {", ".join(fonts) or "system-ui"}
        Sample headlines from their site: {"; ".join(heads) or "N/A"}

        Additional pitch / context from user:
        {pitch or "Position Fetch AI as a strategic partner for their sales team."}

        The microsite is FROM Fetch AI (our product), pitched TO {company}.
        Mirror {company}'s visual style so it feels like it was made for them specifically.
    """).strip()

    try:
        resp = await _openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.55,
            max_tokens=3500,
        )
        html = resp.choices[0].message.content.strip()
        if html.startswith("```"):
            html = html.split("```", 2)[-1].lstrip("html\n")
            if "```" in html:
                html = html[: html.rfind("```")]
    except Exception as exc:
        print(f"[DeckService] GPT-4o failed ({exc}). Using demo.")
        html = _demo_deck(brand, deck_id)

    path = DECKS_DIR / f"{deck_id}.html"
    path.write_text(html, encoding="utf-8")
    return f"/static/decks/{deck_id}.html"


def _demo_deck(brand: dict, deck_id: str) -> str:
    company = brand["company_name"]
    tagline = brand.get("tagline", "Built for teams that move fast.")
    colors  = brand.get("colors", [])
    primary = colors[0] if colors else "#F5A623"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Fetch AI — Built for {company}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0A0A0A;color:#fff;font-family:system-ui,sans-serif;line-height:1.6}}
.wrap{{max-width:720px;margin:0 auto;padding:0 24px}}
nav{{border-bottom:1px solid rgba(255,255,255,.07);padding:18px 0;display:flex;align-items:center;gap:12px}}
.dot{{width:10px;height:10px;background:{primary};border-radius:50%}}
.brand{{font-weight:700;font-size:18px}}
.hero{{padding:72px 0 48px;text-align:center}}
.badge{{display:inline-block;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);color:rgba(255,255,255,.7);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;padding:5px 14px;border-radius:99px;margin-bottom:24px}}
h1{{font-size:42px;font-weight:900;letter-spacing:-.03em;line-height:1.1;margin-bottom:16px}}
h1 span{{color:{primary}}}
.sub{{color:rgba(255,255,255,.45);font-size:17px;max-width:520px;margin:0 auto 36px}}
.btn{{display:inline-block;background:{primary};color:#000;font-weight:800;padding:14px 32px;border-radius:10px;text-decoration:none;border:none;cursor:pointer;font-size:15px;box-shadow:0 0 24px rgba(245,166,35,.3)}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:48px 0}}
.card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:24px}}
.card .icon{{font-size:24px;margin-bottom:12px}}
.card h3{{font-size:15px;font-weight:700;margin-bottom:6px}}
.card p{{font-size:13px;color:rgba(255,255,255,.4)}}
.cta{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:48px;text-align:center;margin-bottom:64px}}
footer{{border-top:1px solid rgba(255,255,255,.05);padding:24px 0;text-align:center;font-size:12px;color:rgba(255,255,255,.2)}}
</style>
</head>
<body>
<div class="wrap">
<nav><div class="dot"></div><div class="brand">Fetch AI</div></nav>
<div class="hero">
  <div class="badge">Custom-built for {company}</div>
  <h1>Close {company}<br><span>Faster.</span></h1>
  <p class="sub">{tagline}</p>
  <button id="cta" class="btn">See It In Action</button>
</div>
<div class="grid">
  <div class="card"><div class="icon">⚡</div><h3>10-Second Enrichment</h3><p>Real-time firmographics, intent signals, and news from 20+ sources — instantly.</p></div>
  <div class="card"><div class="icon">✉️</div><h3>AI Email Drafts</h3><p>GPT-4o writes hyper-personalized outreach referencing your prospect's exact context.</p></div>
  <div class="card"><div class="icon">🎯</div><h3>Live Tracking</h3><p>Know the second a prospect opens your microsite or clicks pricing. Strike immediately.</p></div>
</div>
<div class="cta">
  <h2 style="font-size:28px;font-weight:900;margin-bottom:12px">Ready to see Fetch AI live?</h2>
  <p style="color:rgba(255,255,255,.45);margin-bottom:28px">This page was generated for {company} in seconds. Imagine your whole pipeline like this.</p>
  <button class="btn" onclick="document.getElementById('cta').click()">Book a 15-Min Demo</button>
</div>
</div>
<footer>Fetch AI · Built for {company} · Confidential</footer>
</body>
</html>"""
