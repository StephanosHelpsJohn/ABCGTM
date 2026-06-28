/**
 * Fetch AI — Orange Slice enrichment script
 * Usage: node scripts/enrich.mjs <domain> <persona>
 * Outputs a single JSON object to stdout.
 */
import { services } from 'orangeslice';

const domain  = process.argv[2];
const persona = process.argv[3] || 'VP Sales';

if (!domain) {
  console.error('Usage: node scripts/enrich.mjs <domain> <persona>');
  process.exit(1);
}

// Run all three enrichment sources in parallel
const [company, newsResult, techResult] = await Promise.allSettled([
  services.company.linkedin.enrich({ domain, extended: true }),

  services.predictLeads.companyNewsEvents({
    company_id_or_domain: domain,
    limit: 8,
    categories: [
      'receives_financing',
      'launches',
      'hires',
      'increases_headcount_by',
      'expands_offices_in',
      'expands_offices_to',
      'signs_new_client',
      'partners_with',
    ],
  }),

  services.predictLeads.companyTechnologyDetections({
    company_id_or_domain: domain,
    limit: 30,
  }),
]);

// ── Company (LinkedIn + Crunchbase) ──────────────────────────────────────────
const co = company.status === 'fulfilled' ? company.value : null;

const funding = co?.crunchbase_funding ?? [];
const latestRound = funding.length > 0
  ? funding.sort((a, b) => new Date(b.round_date) - new Date(a.round_date))[0]
  : null;

const growthYoY = co?.employee_growth_12mo
  ? `${((co.employee_growth_12mo - 1) * 100).toFixed(1)}%`
  : null;

// ── News events ───────────────────────────────────────────────────────────────
const newsEvents = newsResult.status === 'fulfilled'
  ? (newsResult.value?.data ?? []).slice(0, 5).map(e => e.attributes.summary)
  : [];

// ── Tech stack ────────────────────────────────────────────────────────────────
const techNames = techResult.status === 'fulfilled'
  ? (techResult.value?.included ?? [])
      .filter(i => i.type === 'technology')
      .map(i => i.attributes.name)
      .slice(0, 15)
  : [];

// ── Build output ──────────────────────────────────────────────────────────────
const output = {
  domain,
  company_name:   co?.name   ?? domain.split('.')[0].charAt(0).toUpperCase() + domain.split('.')[0].slice(1),
  description:    co?.description ?? null,
  industry:       co?.industry ?? null,
  employee_count: co?.employee_count ? String(co.employee_count) : 'Unknown',
  employee_growth_yoy: growthYoY,
  company_size:   co?.company_size ?? null,
  hq:             [co?.locality, co?.region, co?.country_name].filter(Boolean).join(', ') || 'Unknown',
  founded_year:   co?.founded_year ?? null,
  linkedin_url:   co?.linkedin_url ?? null,
  website:        co?.website ?? `https://${domain}`,

  // Funding
  latest_round:   latestRound ? {
    round:    latestRound.round_name,
    amount:   latestRound.round_amount,
    currency: latestRound.round_currency,
    date:     latestRound.round_date,
    investors: latestRound.investor_names ?? [],
  } : null,
  total_funding_rounds: funding.length,

  // Signals
  tech_stack:     techNames,
  recent_news:    newsEvents,

  // Intent signals derived from what we found
  intent_signals: [
    ...(latestRound ? [`Recently raised ${latestRound.round_name ?? 'funding'} — likely scaling sales & ops`] : []),
    ...(growthYoY && parseFloat(growthYoY) > 10 ? [`${growthYoY} YoY headcount growth — actively hiring`] : []),
    ...(techNames.length > 0 ? [`Tech stack includes ${techNames.slice(0,4).join(', ')} — existing tooling to integrate with`] : []),
    ...(newsEvents.length > 0 ? [newsEvents[0]] : []),
  ].slice(0, 4),

  target_persona: persona,
};

process.stdout.write(JSON.stringify(output));
