/**
 * Fetch AI — Buy Signal Scanner
 * Usage: node scripts/scan_events.mjs <domain> [keyword1,keyword2,...]
 * Outputs JSON with news events and job postings that match buy signals.
 */
import { services } from 'orangeslice';

const domain   = process.argv[2];
const keywords = (process.argv[3] || '').split(',').map(k => k.trim().toLowerCase()).filter(Boolean);

if (!domain) {
  console.error('Usage: node scripts/scan_events.mjs <domain> [keywords]');
  process.exit(1);
}

const [newsResult, jobsResult, companyResult] = await Promise.allSettled([
  services.predictLeads.companyNewsEvents({
    company_id_or_domain: domain,
    limit: 15,
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

  services.predictLeads.companyJobOpenings({
    company_id_or_domain: domain,
    active_only: true,
    limit: 20,
    categories: ['sales', 'marketing', 'management', 'operations'],
  }),

  services.company.linkedin.enrich({ domain, extended: false }),
]);

// Parse news events
const rawNews = newsResult.status === 'fulfilled'
  ? (newsResult.value?.data ?? [])
  : [];

const newsEvents = rawNews.map(e => ({
  type: 'news',
  category: e.attributes?.category ?? 'news',
  summary: e.attributes?.summary ?? '',
  date: e.attributes?.occurred_at ?? null,
  url: e.attributes?.url ?? null,
}));

// Parse job openings
const rawJobs = jobsResult.status === 'fulfilled'
  ? (jobsResult.value?.data ?? [])
  : [];

const jobOpenings = rawJobs.map(j => ({
  type: 'job',
  category: j.attributes?.category ?? 'job_opening',
  title: j.attributes?.title ?? 'Role',
  location: j.attributes?.location ?? null,
  url: j.attributes?.url ?? null,
  date: j.attributes?.first_seen_at ?? null,
}));

// Company basics
const co = companyResult.status === 'fulfilled' ? companyResult.value : null;

// Filter by keywords if provided
function matchesKeywords(text) {
  if (keywords.length === 0) return true;
  const t = (text || '').toLowerCase();
  return keywords.some(k => t.includes(k));
}

const filteredNews = keywords.length
  ? newsEvents.filter(e => matchesKeywords(e.summary) || matchesKeywords(e.category))
  : newsEvents;

const filteredJobs = keywords.length
  ? jobOpenings.filter(j => matchesKeywords(j.title) || matchesKeywords(j.category))
  : jobOpenings;

const output = {
  domain,
  company_name: co?.name ?? domain.split('.')[0].charAt(0).toUpperCase() + domain.split('.')[0].slice(1),
  industry: co?.industry ?? null,
  employee_count: co?.employee_count ?? null,
  news_events: filteredNews.slice(0, 8),
  job_openings: filteredJobs.slice(0, 10),
  total_signals: filteredNews.length + filteredJobs.length,
};

process.stdout.write(JSON.stringify(output));
