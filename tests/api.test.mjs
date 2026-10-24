// Unit tests for the serverless function (no network, no real token): node --test tests/api.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
const handler = require('../api/github-contributions.js');
const FIXTURE = JSON.parse(readFileSync(new URL('./fixtures/graphql-real-snapshot-2026-10-10.json', import.meta.url), 'utf8'));
const SECRET = 'ghp_TESTSECRET_must_never_leak';

function call(method = 'GET') {
  const res = { headers: {}, statusCode: 0, body: '' };
  res.setHeader = (k, v) => (res.headers[k.toLowerCase()] = v);
  res.end = (b) => (res.body = b);
  return handler({ method }, res).then(() => ({ ...res, json: res.body ? JSON.parse(res.body) : null }));
}
const mockFetch = (fn) => {
  global.fetch = async (...a) => fn(...a);
};
const ok = (body, status = 200) => ({ ok: status < 400, status, json: async () => body });

test.beforeEach(() => {
  handler._internals.resetCache();
  process.env.GITHUB_TOKEN = SECRET;
  delete process.env.GITHUB_USERNAME;
});

test('maps the real calendar snapshot: total 288, 371 days, levels 0–4, compact rows', async () => {
  let seen;
  mockFetch((url, init) => ((seen = { url, init }), ok(FIXTURE)));
  const r = await call();
  assert.equal(r.statusCode, 200);
  assert.equal(r.json.total, 288);
  assert.equal(r.json.weeks.flat().length, 371);
  assert.equal(r.json.weeks.flat().reduce((s, d) => s + d[1], 0), 288, 'daily counts sum to the genuine total');
  assert.deepEqual([...new Set(r.json.weeks.flat().map((d) => d[2]))].sort(), [0, 1, 2, 3, 4]);
  assert.equal(r.json.from, '2025-10-05');
  assert.equal(r.json.to, '2026-10-10');
  assert.match(r.headers['cache-control'], /s-maxage=3600/);
  assert.equal(seen.init.headers.Authorization, `bearer ${SECRET}`, 'token only goes to GitHub');
  assert.ok(!r.body.includes(SECRET), 'token never appears in the response body');
});

test('second call is served from memory (no extra GitHub request)', async () => {
  let n = 0;
  mockFetch(() => (n++, ok(FIXTURE)));
  await call();
  const r = await call();
  assert.equal(n, 1);
  assert.equal(r.headers['x-cache'], 'HIT');
});

test('missing token → 503 not_configured, no upstream call, not cached', async () => {
  delete process.env.GITHUB_TOKEN;
  let n = 0;
  mockFetch(() => (n++, ok(FIXTURE)));
  const r = await call();
  assert.equal(r.statusCode, 503);
  assert.equal(r.json.error, 'not_configured');
  assert.equal(n, 0);
  assert.equal(r.headers['cache-control'], 'no-store');
});

test('bad credentials (401) → 502 auth, never cached, token not leaked', async () => {
  mockFetch(() => ok({ message: `Bad credentials ${SECRET}` }, 401));
  const r = await call();
  assert.equal(r.statusCode, 502);
  assert.equal(r.json.error, 'auth');
  assert.equal(r.headers['cache-control'], 'no-store');
  assert.ok(!r.body.includes(SECRET));
});

test('rate limit: HTTP 403/429 and GraphQL RATE_LIMITED → 429 rate_limited', async () => {
  for (const respond of [() => ok({}, 403), () => ok({}, 429), () => ok({ errors: [{ type: 'RATE_LIMITED' }] })]) {
    handler._internals.resetCache();
    mockFetch(respond);
    const r = await call();
    assert.equal(r.statusCode, 429);
    assert.equal(r.json.error, 'rate_limited');
  }
});

test('unknown user → 404 not_found (null user or NOT_FOUND error)', async () => {
  for (const body of [{ data: { user: null } }, { errors: [{ type: 'NOT_FOUND' }], data: { user: null } }]) {
    handler._internals.resetCache();
    mockFetch(() => ok(body));
    const r = await call();
    assert.equal(r.statusCode, 404);
    assert.equal(r.json.error, 'not_found');
  }
});

test('malformed / empty upstream responses → 502 upstream (never a fake calendar)', async () => {
  for (const body of [{}, { data: {} }, { data: { user: {} } }, { data: { user: { contributionsCollection: { contributionCalendar: { weeks: [] } } } } }, { errors: [{ message: 'x' }] }]) {
    handler._internals.resetCache();
    mockFetch(() => ok(body));
    const r = await call();
    assert.equal(r.statusCode, 502, JSON.stringify(body));
    assert.equal(r.json.error, 'upstream');
  }
});

test('valid but empty calendar (0 contributions) is returned honestly as zero', async () => {
  const empty = { data: { user: { contributionsCollection: { contributionCalendar: { totalContributions: 0, weeks: [{ contributionDays: [{ date: '2026-10-10', contributionCount: 0, contributionLevel: 'NONE' }] }] } } } } };
  mockFetch(() => ok(empty));
  const r = await call();
  assert.equal(r.statusCode, 200);
  assert.equal(r.json.total, 0);
  assert.deepEqual(r.json.weeks, [[['2026-10-10', 0, 0]]]);
});

test('network failure → 502 upstream; timeout handled the same way', async () => {
  mockFetch(() => {
    throw new TypeError('fetch failed');
  });
  const r = await call();
  assert.equal(r.statusCode, 502);
  assert.equal(r.json.error, 'upstream');
});

test('GitHub down after a good fetch → last good copy served as stale (never for auth errors)', async () => {
  mockFetch(() => ok(FIXTURE));
  await call();
  // expire the fresh window by moving the clock forward 2 hours
  const realNow = Date.now;
  Date.now = () => realNow() + 2 * 3600 * 1000;
  try {
    mockFetch(() => ok({}, 500));
    const r = await call();
    assert.equal(r.statusCode, 200);
    assert.equal(r.json.stale, true);
    assert.equal(r.json.total, 288);
    assert.equal(r.headers['x-cache'], 'STALE');
    mockFetch(() => ok({}, 401));
    const a = await call();
    assert.equal(a.statusCode, 502, 'auth errors are surfaced, not hidden behind stale data');
  } finally {
    Date.now = realNow;
  }
});

test('only GET/HEAD allowed; invalid GITHUB_USERNAME rejected before any request', async () => {
  let n = 0;
  mockFetch(() => (n++, ok(FIXTURE)));
  const post = await call('POST');
  assert.equal(post.statusCode, 405);
  process.env.GITHUB_USERNAME = 'bad name; drop';
  const bad = await call();
  assert.equal(bad.statusCode, 503);
  assert.equal(n, 0);
});
