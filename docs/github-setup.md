# GitHub contribution calendar — setup

The calendar is served by a Vercel Serverless Function (`api/github-contributions.js`) that calls the GitHub GraphQL API.
The token only ever exists in Vercel's environment; the browser never sees it and it is never committed.

## Environment variables
| Name | Required | Value |
|---|---|---|
| `GITHUB_TOKEN` | yes | a GitHub personal access token (see below) |
| `GITHUB_USERNAME` | no | defaults to `moustafax7-dotcom` |

## 1. Create the token
1. GitHub → Settings → Developer settings → Personal access tokens → **Tokens (classic)** → Generate new token (classic).
2. Name it e.g. `portfolio-contributions`, choose an expiry you can remember (set a reminder to rotate it).
3. **Leave every scope unchecked.** A scope-less token can read public data only, so it cannot reach private repositories. That is all the calendar needs.
4. Copy the token once; GitHub will not show it again.

## 2. Add it to Vercel
1. Vercel → your project → Settings → Environment Variables.
2. Add `GITHUB_TOKEN` (Production and Preview; tick **Sensitive**). Optionally add `GITHUB_USERNAME`.
3. **Redeploy** — Vercel applies environment changes only to new deployments.

Local testing: `cp .env.example .env.local`, fill in the token, run `vercel dev`, open http://localhost:3000. (`.env*` is git-ignored.)

## 3. Verify it matches your profile
    node scripts/verify-contributions.mjs https://mustafa-portfolio-lyart.vercel.app
It fetches the function output and the public graph on github.com and compares the total and every day's count and intensity level. Exit code 0 means identical.
If totals differ, the usual reason is private-contribution visibility (see below) or a contribution made between the two requests.

## What the function does
- `GET /api/github-contributions` → `{ username, total, from, to, weeks: [[[date, count, level 0-4], …], …], generatedAt }`.
- `level` is GitHub's own `contributionLevel`; nothing is computed or generated.
- Caching: CDN `s-maxage=3600` + `stale-while-revalidate=86400`, browser `max-age=300`, in-memory copy for 1 hour. If GitHub fails, the last good copy (≤ 24 h) is served with `"stale": true` and the page says so. Auth errors are never hidden behind stale data.
- Errors (never forward upstream messages): `not_configured` 503, `auth` 502, `rate_limited` 429, `not_found` 404, `upstream` 502, `method_not_allowed` 405.

## Private contributions
The graph shows what GitHub's contribution calendar contains for your account. Whether private activity appears depends on your profile setting
(*Profile → Contributions → "Private contributions"*) and is the same information your public profile shows. The function never receives repository names or details — only per-day counts and levels.
I could not test the real token from my environment, so run the verify script after deploying; if it reports differences, tell me the output.

## Troubleshooting
| Page shows | Cause |
|---|---|
| "not enabled on this deployment yet" | `GITHUB_TOKEN` missing, or you did not redeploy after adding it, or the site runs on a plain static server (no `/api`) |
| "temporarily unavailable" | token revoked/expired (function logs `auth`) — create a new one and redeploy |
| "request limit was reached" | GitHub rate limit; it recovers on its own, the CDN cache absorbs most traffic |
