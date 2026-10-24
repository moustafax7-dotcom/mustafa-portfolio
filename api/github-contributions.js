'use strict';
/**
 * Vercel Serverless Function — GET /api/github-contributions
 *
 * Returns the real GitHub contribution calendar (the data behind the profile heatmap)
 * using the GraphQL API. The token stays on the server.
 *
 * Environment variables (set in Vercel → Project → Settings → Environment Variables):
 *   GITHUB_TOKEN     required  Personal access token. A classic token with NO scopes is enough
 *                              (it reads public data only, so private repositories are never accessible).
 *   GITHUB_USERNAME  optional  Defaults to "moustafax7-dotcom".
 *
 * Response (200): { username, total, from, to, weeks: [[[date, count, level], …], …], generatedAt, stale? }
 *   level is GitHub's own intensity (0 = none … 4 = most), never computed here.
 * Errors: { error: <code> } with codes: not_configured (503), auth (502), rate_limited (429),
 *   not_found (404), upstream (502), method_not_allowed (405). Upstream messages are never forwarded.
 */

const DEFAULT_USERNAME = 'moustafax7-dotcom';
const GRAPHQL_URL = 'https://api.github.com/graphql';
const FRESH_MS = 60 * 60 * 1000; // serve from memory for 1 hour
const STALE_MS = 24 * 60 * 60 * 1000; // if GitHub fails, serve the last good copy for up to 24 hours
const TIMEOUT_MS = 8000;

const QUERY = `query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}`;

const LEVELS = { NONE: 0, FIRST_QUARTILE: 1, SECOND_QUARTILE: 2, THIRD_QUARTILE: 3, FOURTH_QUARTILE: 4 };

class ApiError extends Error {
  constructor(code, status) {
    super(code);
    this.code = code;
    this.status = status;
  }
}

// Per-instance memory cache (the CDN cache headers below do the heavy lifting across instances).
let memory = null; // { at, username, payload }

function send(res, status, body, cacheControl) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', cacheControl);
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.end(JSON.stringify(body));
}

const OK_CACHE = 'public, max-age=300, s-maxage=3600, stale-while-revalidate=86400';

/** Maps GitHub's GraphQL response to the compact payload. Throws ApiError for anything unexpected. */
function toPayload(json, username) {
  const errors = Array.isArray(json && json.errors) ? json.errors : [];
  if (errors.some((e) => e && e.type === 'RATE_LIMITED')) throw new ApiError('rate_limited', 429);
  if (errors.some((e) => e && e.type === 'NOT_FOUND')) throw new ApiError('not_found', 404);
  if (errors.length) throw new ApiError('upstream', 502);

  const user = json && json.data && json.data.user;
  if (user === null) throw new ApiError('not_found', 404);
  const calendar = user && user.contributionsCollection && user.contributionsCollection.contributionCalendar;
  if (!calendar || !Array.isArray(calendar.weeks) || !Number.isFinite(calendar.totalContributions)) {
    throw new ApiError('upstream', 502);
  }

  const weeks = calendar.weeks.map((week) =>
    (week.contributionDays || []).map((d) => [d.date, d.contributionCount, LEVELS[d.contributionLevel] ?? 0])
  );
  const flat = weeks.flat();
  return {
    username,
    total: calendar.totalContributions,
    from: flat.length ? flat[0][0] : null,
    to: flat.length ? flat[flat.length - 1][0] : null,
    weeks,
    generatedAt: new Date().toISOString(),
  };
}

async function fetchCalendar(username, token) {
  let response;
  try {
    response = await fetch(GRAPHQL_URL, {
      method: 'POST',
      headers: {
        Authorization: `bearer ${token}`,
        'Content-Type': 'application/json',
        'User-Agent': 'portfolio-contributions-function',
      },
      body: JSON.stringify({ query: QUERY, variables: { login: username } }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    throw new ApiError('upstream', 502); // network failure or timeout
  }

  if (response.status === 401) throw new ApiError('auth', 502);
  if (response.status === 403 || response.status === 429) throw new ApiError('rate_limited', 429);
  if (!response.ok) throw new ApiError('upstream', 502);

  let json;
  try {
    json = await response.json();
  } catch {
    throw new ApiError('upstream', 502);
  }
  return toPayload(json, username);
}

async function handler(req, res) {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD');
    return send(res, 405, { error: 'method_not_allowed' }, 'no-store');
  }

  const token = process.env.GITHUB_TOKEN;
  const username = (process.env.GITHUB_USERNAME || DEFAULT_USERNAME).trim();
  if (!token) return send(res, 503, { error: 'not_configured' }, 'no-store');
  if (!/^[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}$/i.test(username)) return send(res, 503, { error: 'not_configured' }, 'no-store');

  const now = Date.now();
  if (memory && memory.username === username && now - memory.at < FRESH_MS) {
    res.setHeader('X-Cache', 'HIT');
    return send(res, 200, memory.payload, OK_CACHE);
  }

  try {
    const payload = await fetchCalendar(username, token);
    memory = { at: now, username, payload };
    res.setHeader('X-Cache', 'MISS');
    return send(res, 200, payload, OK_CACHE);
  } catch (error) {
    const code = error instanceof ApiError ? error.code : 'upstream';
    console.error(`github-contributions: ${code}`); // never log the token or upstream bodies

    if (memory && memory.username === username && now - memory.at < STALE_MS && code !== 'auth') {
      res.setHeader('X-Cache', 'STALE');
      return send(res, 200, { ...memory.payload, stale: true }, 'public, max-age=60, s-maxage=60');
    }
    const status = error instanceof ApiError ? error.status : 502;
    return send(res, status, { error: code }, code === 'auth' ? 'no-store' : 'public, max-age=30, s-maxage=60');
  }
}

module.exports = handler;
module.exports._internals = { toPayload, resetCache: () => { memory = null; } };
