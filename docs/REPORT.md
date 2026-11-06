# Portfolio v4 — Sushi Bounce parity with the reference source + P0 mobile performance fix

Built on v3 (GitHub dashboard) which includes v2 (certificates + games). **Nothing committed, pushed or deployed.**

## A. Sushi Bounce — reference vs. my implementation
I analysed the three files you supplied (`plugin.js` ≈ lines 485–690, the `.sushi-*` CSS, the page HTML). Earlier I could only see the rendered text; everything below is now read from source.

| Mechanic | Reference (verified in source) | Mine |
|---|---|---|
| Board | `min(700px,100%)` × 430 px (380 px on viewports ≤ 700 px) | same sizes |
| Sushi box | 42 px | 42 px (drawn nigiri, original art) |
| Paddle | 110×15, 22 px above the bottom (95×14, 20 px on ≤ 700 px) | same |
| Start state | x = centre, y = 80, vx = ±3 (random sign), vy = +3 px **per frame** | same, in 60 Hz steps |
| Walls / ceiling | clamp + flip | same |
| Paddle hit | moving down, bottom ≥ paddle top, top ≤ paddle bottom, **sushi centre-x within the paddle**; snaps to the top, score +1 | same (tested at the exact edges) |
| Bounce | always 45°: `vx = ±speed` (sign kept), `vy = −speed` | same (no angle control) |
| Difficulty | `speed = 3 + min(score × 0.08, 3)` (cap 6 at score 38) | same (tested 1/10/38/39/101) |
| Life lost | sushi top edge below the board; −1 life; respawn at once, score + paddle kept | same |
| Game over | 0 lives: 🍣, "Oops!", "Your sushi escaped.", Play Again | same texts |
| Restart | score 0, lives 3, positions and velocities reset | same |
| Controls | ← → (35 px per keydown), mouse move, touch drag | all three (see differences) |
| HUD | "SCORE n", "LIVES n" | same labels/values (+ small sushi icons) |

### Intentional differences (the reference weaknesses I did not copy)
1. **Start screen + Start button.** The reference starts on page load and loops forever even when off-screen. Mine only runs after "Start Game", and the loop is stopped whenever the game is not playing.
2. **Fixed 60 Hz physics.** The reference moves "3 px per animation frame", so it runs 2× faster on a 120 Hz screen. Mine converts real time to 1/60 s steps (tested: identical position after 1 s at 60/120/144 Hz).
3. **Hit-box vs. picture.** In the reference the box is positioned by `left/top` but CSS applies `translate(-50%,-50%)`, so the picture sits 21 px up-left of the box it collides with (it visibly bounces ~21 px above the paddle and half-leaves the board at the walls). Mine draws the sushi exactly where it collides.
4. **Paddle consistency.** The reference CSS uses `bottom: 20px` on phones but the JS assumes 22 px (2 px mismatch). Mine uses 20 px on phones for both.
5. **Pointer offset.** The reference subtracts the board's border-box left from the pointer but positions the paddle inside the border (≈3 px off). Mine centres the paddle on the pointer.
6. **Keyboard.** Reference: 35 px per `keydown` event (speed depends on the OS key-repeat rate) and it calls `preventDefault` on arrow keys for the whole page while "running" — i.e. always, so the page cannot be scrolled with arrows. Mine: first press nudges 35 px, holding moves at 720 px/s, A/D also work, and arrows are captured **only while the game is playing and on screen**.
7. **Touch.** Reference uses `touch-action: none` + `preventDefault` on touchmove, so a finger on the board cannot scroll the page. Mine uses `touch-action: pan-y`: horizontal drags move the paddle, vertical swipes scroll. Plus on-screen ◀ ▶ buttons on touch devices.
8. **Added (not in the reference):** pause (P / Esc / button), auto-pause when the tab is hidden or the game scrolls away, screen-reader announcements, reduced-motion handling (no red flash, no spin), DPR-aware canvas, cached static background, no emoji in the board (original drawing; 🍣 only appears as a character on the game-over card).
9. **Visuals** follow the portfolio (colours, type, rounded board), not the reference's red border/sticker look.

Tests for all of this: `tests/features.py` (81 checks, 31 of them Sushi).

## B. P0 — mobile TBT regression
### Root cause (evidence, not guesses)
Profile: Chrome, mobile emulation, **4× CPU throttle**, same machine, 5 runs per version:

| | v1 | v2 | final |
|---|---|---|---|
| main-thread task time in 5 s | 2777 ms | 2797 ms | **1341 ms (−52 %)** |
| layouts / style recalcs | 184 / 244 | 176 / 235 | **63 / 104** |

Per-effect cost (disable one thing, 3 runs each): decorative **glows −602 ms**, `.cv-shine` (animated `left` ⇒ a layout every frame, forever) **−387 ms and 211 → 62 layouts**, hero dot canvas −162 ms, pulsing dots (animated `box-shadow`) −159 ms, floating chips −84 ms; all CSS animations together **−1533 ms**. A separate hot spot: `initCustomCursor` called `matchMedia` at start-up, forcing a synchronous style+layout pass (~200 ms @4×). A section-by-section bisect showed no single section dominates the first layout (cost is spread across the page).
These existed since v1, so v2's extra HTML/JS/DOM (+13 KB HTML, certificates, games shell) was added on top of an already saturated main thread → the regression. *Correction to my earlier reply:* I first called v1-vs-v2 "within noise"; interleaved batches showed it is real (below).

### Fixes (each measured)
`.cv-shine` → `transform`; pulse dots / loader pulse → `opacity/transform` (no box-shadow); glows promoted + `contain`; all hero animations pause while the hero is off-screen (`html.hero-off`); ≤ 900 px / touch: no looping decorative motion, dot field is a static CSS pattern; the dot **canvas only on desktop with a fine pointer**; the custom cursor is set up on the **first real mouse move** (no start-up `matchMedia`); certificate viewer: no `backdrop-filter`, no `overflow` toggle on `<html>` (forced a full relayout), instant preview from the cached thumbnail, neighbour preloading when idle; game canvas draws a pre-rendered background. Games/GitHub/viewer remain lazy (0 requests for them on first paint — tested).
Tried and **rejected** (no consistent gain in 5-run medians): `content-visibility:auto` (also broke anchor jumps), `contain: layout/style/content` on sections, `min-width` reset.

### Lighthouse (mobile, simulated throttling, interleaved runs, medians; lab ≠ field)
Batch 1 — plain server (no compression), 5 runs each:

| | Score | TBT | LCP | TTI | Speed Index | CLS |
|---|---|---|---|---|---|---|
| v1 (improved) | 82 | 308 (149–470) | 3212 | 4018 | 4730 | 0.018 |
| v2 | 77 | 373 (358–448) | 3383 | 4374 | 4715 | 0.018 |
| v3 | 80 | 372 | 3008 | 4189 | 4791 | 0.017 |
| **final** | **85** | 320 (249–520) | **3007** | **3308** | **3321** | **0.002** |

Batch 2 — served **with gzip** (closer to Vercel), 4 runs each:

| | Score | TBT | LCP | TTI | Speed Index | CLS | transfer |
|---|---|---|---|---|---|---|---|
| v1 | 94 | **125** (86–164) | 2422 | 3348 | 4547 | 0.018 | 165 KB |
| v2 | 82 | 454 | 2679 | 3994 | 4613 | 0.018 | 173 KB |
| **final** | 90 | 340 (285–506) | **1890** | **2592** | **3139** | **0.002** | 178 KB |

An earlier busier-machine batch (6 runs) gave v1 594 / v2 930 / v3 758 / final 409 ms TBT — lab TBT moves ±150 ms between runs and batches; only the ordering within a batch is meaningful. Accessibility 100 / SEO 100 / best-practices 100 for the final (v1/v2: 96).

### Honest verdict on the targets
- **TBT ≤ the 420 ms baseline:** met in every batch (320 / 340 / 409 ms).
- **Back to v1's level:** met without compression (320 vs 308, ranges overlap); **not met with gzip** (340 vs 125) — v1's TBT there was unusually low. I could not find a cause I could prove: the 4×-CPU trace shows the final has fewer long tasks than v1 (5 vs 6) and the same ~430 ms first layout; it just runs slightly later because `main.js` is bigger. Remaining bottleneck = that one large first layout (whole-page cost) and `main.js` size. Next step if you want it: split `main.js` per section and/or minify CSS/JS.
- **LCP / CLS / Speed Index / TTI:** clearly better than v1 and v2 (gzip LCP 1.89 s < 2.5 s target; CLS 0.002).
- **Mobile Lighthouse score:** better than v2 in both batches; vs v1: +3 (plain) / −4 (gzip).
- TBT is a lab metric; real-user INP is not measured here.

### Interaction and game performance (4× CPU, Chromium, `tests/perf.py`)
Tap/keypress timings: certificate filter ≈ 100–130 ms, next certificate ≈ 100–135 ms, Bug Hunter answer ≈ 95–190 ms, Sushi "Start Game" ≈ 90–130 ms (all < 200 ms). **Opening the certificate viewer ≈ 160–230 ms — borderline** (native modal makes the whole page inert; reduced from ≈ 256 ms by the changes above). First open of a game (dynamic import + mount): Bug Hunter ≈ 180 ms, Sushi ≈ 160 ms. During 240 frames of Sushi at 4× CPU: median frame 16.7 ms, p95 16.8 ms, no long task.

## C. Tests (all executed on the final code)
`tests/regression.py` 51/51 · `tests/features.py` 81/81 · `tests/github.py` 43/43 · `tests/perf.py` 14/14 · `node --test tests/api.test.mjs` 11/11 → **200 checks**. They cover Sushi gameplay, Bug Hunter, certificate gallery + lightbox, GitHub integration (mocked), contact form, mobile navigation, keyboard accessibility, reduced motion, console errors, and layout at 360/390/768/1200/1440 px. New `perf.py` guards: looping animations may only use transform/opacity, layout/recalc budgets at 4× CPU, laziness of games/GitHub/certificates, hero pause when off-screen, interaction and frame-time budgets.
Not tested: Safari/Firefox, real phones (real vertical swipe over the canvas, real touch latency), screen readers, Vercel's real CDN, field data (CrUX/INP).

## D. Limitations and what I need from you
1. Sushi parity is from the **source files**, not from watching the game run (the live site is unreachable from my environment). Colours, art and the portfolio frame are intentionally mine.
2. TBT vs v1 under gzip not fully recovered (see verdict). Mobile no longer animates glows/chips/ring (design trade-off; desktop unchanged).
3. Certificate viewer open time is borderline at 4× CPU.
4. Open items from earlier reports are unchanged: Formspree form ID, `GITHUB_TOKEN` in Vercel + redeploy (`docs/github-setup.md`), the 3 hidden projects, LinkedIn URL, `HIDDEN_REPOS`, certificate privacy (Student ID / certificate code on two certificates).

## E. Production-readiness assessment
**Functionally ready, performance improved but not a clean win everywhere.** No failing test, no console errors, LCP/CLS/Speed Index/TTI improved, TBT within your 420 ms target. I would **not** call it fully production-ready until you (1) deploy to a **Vercel preview**, run PageSpeed Insights on that URL (real gzip/brotli + CDN) and confirm TBT, (2) set the Formspree ID and `GITHUB_TOKEN`, and (3) try the games on a real phone. I have not committed, pushed or deployed anything.

---

# Portfolio v3 — GitHub dashboard with a real contribution calendar (update)

Built on `mustafa-portfolio-v2.zip`; nothing removed. **Nothing committed, pushed or deployed.** Setup steps: `docs/github-setup.md`.

## What changed
| Area | Result |
|---|---|
| Contribution calendar | GitHub-style yearly heatmap from the **real** calendar: daily counts, GitHub's own intensity levels (0–4), genuine total in the title ("288 contributions in the last year"), month labels, Mon/Wed/Fri row labels, Less→More legend, link to the real profile. Accessible: labelled grid, one tab stop + arrow keys, per-day `aria-label`/tooltip, live status line, scrolls inside its own region and opens on the latest weeks on phones |
| Secure API | `api/github-contributions.js` (Vercel Serverless Function, GitHub GraphQL). Token only in `GITHUB_TOKEN` (server env). 1 h in-memory + CDN cache, stale-while-error, honest error codes, no upstream messages forwarded, username validated, GET/HEAD only |
| Latest repositories | Newest **6** public repos by `pushed_at`, forks and profile repos skipped, `HIDDEN_REPOS` list in `main.js` for anything else. Each card: name, GitHub's own description (or "No description provided"), language (or "No language detected"), stars, "Updated … ago" (exact date on hover), direct link. Live list labelled "live from GitHub" |
| Static fallback | The verified repos stay as a **separate, labelled snapshot** ("verified snapshot · not live") shown without JS or when GitHub fails. **Fixed:** their descriptions used to be my own wording; they now show the repositories' real descriptions or "No description provided" |
| Dashboard | Public repos / followers / following from the API; language share computed from repositories (not hard-coded), worded "Share of repositories by primary language… not coding proficiency" |
| Performance | Nothing is requested until the section is within 400 px of the viewport (verified: 0 GitHub/`/api` requests on first paint). REST responses cached 30 min in `localStorage`; stale copy shown (clearly labelled) if GitHub is unreachable; refreshes when the tab becomes visible after expiry |
| Bug found & fixed | The nav highlight required 35 % of a section to be visible, so it could never highlight a section taller than the screen (the GitHub section). Now uses a middle-of-viewport band; verified for every section |

## Decisions I made (tell me if you disagree)
1. **Token:** classic PAT with **no scopes** (public data only). Cannot expose private repositories.
2. **Repos/stats go straight from the browser to GitHub's REST API**, cached; only the calendar needs the server. Reason: a token is required only for GraphQL, and this keeps the function tiny. Risk: 60 requests/hour per visitor IP when not cached; the cache + fallback cover it.
3. **`pushed_at`** (not `updated_at`) orders repositories: it changes on real commits; `updated_at` also changes on stars/settings.
4. **Relevance rule:** all non-fork public repos except the profile repos. That currently includes `-React-Summer-Training---ITI`, `fasfoor-project`, `github-practice`, `mustafa-portfolio`, `BT`, `Abdulrahman-Abdulrazek-portfolio`. **You may want to hide some (e.g. `github-practice`, `BT`, friends' portfolios) via `HIDDEN_REPOS`.**
5. Calendar window = GitHub's default last year (what the profile shows). A year picker was not added.
6. Vercel-only (`/api` function). On a static host the calendar shows an honest "not enabled" message.

## Real-data verification (what I could and could not do)
- Fetched your public contribution page on 2026-10-10: **288** contributions, 371 days, 64 active days. The sum of the 371 daily tooltips = 288. Saved as `tests/fixtures/graphql-real-snapshot-2026-10-10.json`; repo list as `…/repos-real-snapshot-…json`. Tests render these real fixtures (follower/following numbers in the mocked user are synthetic).
- `node scripts/verify-contributions.mjs` ran end-to-end (real function code ← real snapshot) against the live github.com profile: **totals 288 = 288 and all 371 days identical (count and level).**
- **Not verified:** the real GraphQL call with *your* token (I have none) — i.e. whether private contributions are included or excluded for your account. Run the verify script after deploying (instructions in `docs/github-setup.md`).

## Tests (executed)
- `node --test tests/api.test.mjs` → **11/11**: real snapshot mapping, memory cache, missing token, 401, 403/429/GraphQL rate limit, unknown user, malformed/empty responses, empty calendar, network failure, stale-on-error (not for auth), method + username validation, token never in responses.
- `python3 tests/github.py` → **43/43**: lazy start (0 requests on first paint, then exactly 2 REST + 1 calendar), 371 days match the fixture exactly, total 288, month/weekday labels, aria-labels, keyboard grid, hover status, no randomness in code, latest-6 ordering, honest descriptions, stats, language share wording, REST 403 / network / bad shape / empty list, cache hit, stale cache note, calendar not-configured / rate-limited / auth / missing function / network / invalid payload / empty / stale, offline + automatic recovery, Try-again button, loading skeleton, nav highlight, five viewports without overflow.
- `python3 tests/features.py` → 72/72 and `python3 tests/regression.py` → 51/51 (3 old GitHub checks moved into `tests/github.py`).
- Not tested: the real token path (above), Safari/Firefox, screen readers, Vercel's real CDN caching.

## Lighthouse (lab, mobile, 4 interleaved runs each; not field data)
| | v2 | v3 |
|---|---|---|
| Performance (median) | 76.5 | 77.5 |
| LCP (median) | 3.44 s | 3.09 s |
| TBT (median) | 457 ms | 400 ms |
| CLS | 0.016–0.018 | 0.016 |
| Best-practices / Accessibility / SEO | 96 / 100 / 100 | **100** / 100 / 100 |
| Transfer (uncompressed) | 306 KB | 321 KB |
Mobile LCP is still above the 2.5 s target in this simulated slow-4G lab (unchanged problem from v1: render delay, blur effects, no gzip on the test server).

## Remaining notes
- Cell size is fixed (11 px) so the calendar is ~780 px wide on desktop, left-aligned, like GitHub's profile view.
- When the function is not configured the browser logs a 503 in the console (normal for a failed fetch).
- Needs from you: create the token + set `GITHUB_TOKEN` in Vercel + redeploy, run the verify script, decide `HIDDEN_REPOS`.

---

# Portfolio v2 — Certificates gallery + Dev Playground (update)

Built on top of `mustafa-portfolio-improved.zip` (nothing from v1 removed). **Nothing committed, pushed or deployed.**

## What was added
| Area | Result |
|---|---|
| Skills | 3 groups (Frontend Development / Data Analysis & Programming / Developer Tools). Added **R** (Devicon glyph, added to the self-hosted subset: font 2.7 KB → 3.0 KB), **SQL** and **Power BI** (small original inline SVGs; Devicon has no Power BI icon). Not added because unconfirmed: Pandas, NumPy, Matplotlib. Moved JavaScript under Frontend |
| Certificates | New section after Experience: 7 real certificates from your 7 uploaded files (nothing invented). Filters (All/Frontend/Data & AI/Training/Other), responsive cards, native `<dialog>` viewer (prev/next, ← →, Esc, close button, backdrop click, swipe, focus trap + restoration, loading and error states). Data lives in `data/certificates.json`; `node scripts/build-certificates.mjs` regenerates the cards. Thumbnails 19–42 KB, full images 83–155 KB |
| Dev Playground | New section after Contact (lowest priority, footer link only). Two tabs. Game modules (`games/*.js`) and nothing else are downloaded only when the section is within 300 px of the viewport (verified: zero requests to `/games/` on first paint) |
| Bug Hunter | 11 questions (7 Easy, 4 Medium), one buggy line each, explanation per question, syntax-highlighted editor with line numbers, progress bar, score, restart, keyboard play (↑ ↓ Enter, keys 1–9) |
| Sushi Bounce | Real canvas game: paddle, bouncing sushi, wall/ceiling bounces, paddle-hit scoring with angle control, 3 lives, game over, Play Again, pause/resume, delta-time loop, DPR-aware resize, auto-pause on hidden tab / off-screen, single rAF that only runs while playing, full listener cleanup, original artwork |
| Content fix | The NTI card said "Frontend Developer" with "Present". Your certificate shows **Web Designer — Summer Training, 16 Aug – 10 Sep 2026, 120 h (90 technical + 30 freelancing), score 84.5%**. The card now says exactly that. Hero/About count is now "7 Certificates" (counted from the gallery) |

## About "exactly like Fattosh" — what I could and could not verify
I could only fetch the reference page's static text (no interactive session, no script access). **Verified from the page:** HUD with *Score* and *Lives* (3), the tagline "Keep the sushi alive!", game-over text "Oops! Your sushi escaped.", a "Play Again" button, and the control hint "← Move →" / drag on mobile. **Not verified (so I did not copy it):** paddle size, ball speed, bounce angle rules, scoring per hit, speed progression, sounds, visuals. These follow the genre (paddle + bouncing object, lose a life when it is missed) and are my own design; numbers are constants at the top of `games/sushi-bounce.js`. **To match it exactly, send a short screen recording** (or screenshots of start / mid-game / game-over) and I will tune speed, paddle width, and scoring to it.

## Tests (executed)
- `python3 tests/regression.py` → **54/54** (v1 suite, updated for 7 certificates).
- `python3 tests/features.py` → **72/72**: gallery (render, 7 thumbnails load, 5 filters, viewer open, next/prev wrap, ←/→, 14-Tab focus trap, Esc + focus restore, close button, backdrop, filter-scoped navigation, swipe, 404 image error state, mobile viewer), Bug Hunter (correct, wrong, double-answer, progression, keyboard, score 4/7, restart, levels, question-bank sanity), Sushi Bounce (start screen, serve → play, paddle keys, no page scroll while playing, centre/off-centre collision, walls, ceiling, 3 lives → game over, Play Again, P/Esc pause, no movement while paused, hidden-tab pause, off-screen pause, canvas resize, listener cleanup, CDP touch drag, on-screen ◀ ▶ buttons), five viewports (360/390/768/1200/1440) with no overflow, reduced motion, skills groups.
- **Not automated / not tested:** a real vertical swipe over the canvas on a physical phone (the sandbox's synthetic scroll gesture does not scroll even plain elements; I verified `touch-action: pan-y` instead), Safari/Firefox, real screen readers, sound (there is none).
- Tests I had to fix were test bugs (aborted mock requests, real game loop interfering). Product bugs the tests found and I fixed: the viewer dialog was pinned to the top-left corner (site-wide `* {margin:0}` removed its auto margin), and Tab could leave the viewer.

## Lighthouse (lab: local server, simulated throttling, headless Chromium — not field data)
Interleaved runs, 4 each, mobile preset. **Previous v1 vs now:** performance median **75 → 70**, TBT median 479 → 556 ms, LCP 3.37 → 3.55 s, FCP 2.11 → 2.25 s, CLS ≈ 0.017 both. Desktop: 98 → 97, LCP 0.9 s both. Accessibility 100, SEO 100, best-practices 96 unchanged. **So the new features cost a few points on mobile in the lab**; main cause is ~20 KB more HTML (the test server does not gzip; Vercel does). Mobile LCP target 2.5 s is still **not met in the lab** (it wasn't in v1 either). Things I tried and rejected: `content-visibility:auto` (made `#section` links land in the wrong place), blocking vs. async `sections.css` (blocking is no better).

## Needs your input / known limitations
1. **Sushi Bounce parity** — send a screen recording (see above).
2. **Certificate privacy:** the NTI certificate shows your Student ID and the Huawei one shows a certificate code + QR. I published the files unmodified (not altering credentials). Tell me if you want those areas covered.
3. **Dates:** the Olympiad and ITIDA Gigs certificates show no date, so none is displayed. Verification links: none exist in the files; add `verifyUrl` in the JSON if you have them.
4. Names on certificates vary (Moustafa / Mostafa, with or without "Abd El Hamid"); shown as issued.
5. Category choices (e.g. Decoding Success Day under Data & AI) are mine; edit `data/certificates.json`.
6. Remaining unconfirmed skills (Pandas, NumPy, Matplotlib): tell me if you really use them.
7. Cards left in the old "Courses" list without a file: SQL (DataCamp), Capital Markets (EGX), CS50. Send their files to add them to the gallery.
8. Previous open items (Formspree ID, 3 hidden projects, LinkedIn URL, live-link check) are unchanged — see the v1 section below.

## Production readiness (v2)
Safe to deploy after the v1 blockers (Formspree ID, live-link check). Games and viewer are tested in Chromium only.

---

# Portfolio audit & optimisation — report

Scope: improvement of the existing vanilla HTML/CSS/JS site. No framework added, no redesign, **nothing committed, pushed or deployed**, no real contact-form submission.
Status labels: **FV** fixed & verified (a test I ran) · **FNT** fixed, not fully tested · **OWNER** needs your input · **DEF** deferred.

## 1. Baseline (Phase 0) — what the source actually showed
| Reported issue | Result |
|---|---|
| Simulated GitHub contribution graph | **Confirmed** (`renderContributionGraph`, seeded pseudo-random cells) |
| `FALLBACK_REPOS` fabricated | **Confirmed.** All four repo names (`ecommerce-react`, `analytics-dashboard`, `ai-task-automator`, `portfolio`) return **404** on GitHub; stars/dates invented. It rendered whenever the API failed or was rate-limited |
| Hard-coded "Top Languages" 45/30/15/10 % | **Confirmed fabricated** (not in the original brief) |
| Inconsistent counts | **Confirmed**: hero 1 live vs 2 "Live & Deployed"; About "4 projects" vs 5 shown; certificates 7+ vs 8+ |
| DEPI active vs completed | **Confirmed** (Education "Active Training", Experience "Completed", bio present tense) |
| Furniture stack says React.js | **Confirmed false**: repo README + file tree = HTML, CSS, JavaScript, Bootstrap (no package.json). Features in README match the site text |
| 3 projects link "Source Code" to the profile | **Confirmed**; no public repo named like them exists (20 public repos checked) |
| "70 %" claim | **Confirmed**, no measurement |
| `.pw/.pchip/.p-ring` vs `photo-*` | **Confirmed**: mobile rules never applied; photo frame stayed 320×400 at 360 px |
| Global `overflow-x:hidden` | **Confirmed masking real overflow**: contribution box 486 px wide at 360 px, photo ring/chips, glows |
| Placeholder `#2a2b38` | **Confirmed: 1.41 : 1** (needs 4.5 : 1) |
| `timeAgo` "0 months" | **Confirmed** for 7–30 days (and `null` → "56 years ago" in my first rewrite — caught by tests) |
| Loader = load + 800 ms | **Confirmed** |
| Base64 CV in JS | **Confirmed** (87 KB JS; decodes to a valid 65 KB PDF) |
| `og:url` → GitHub Pages | **Confirmed** |
| `@latest` devicon | **Confirmed**; also the icon font is **1.5 MB** for 11 icons |
| Formspree ID | **OWNER**: endpoint is `/f/moustafa`; the original code comment says to replace it. Could not be tested from the sandbox |
| Not in your list, found | Linux icon `#000` on dark card (1.11 : 1, invisible); C++ icon 1.93 : 1; native cursor hidden globally even without JS; no `<main>`, skip link, labels, `aria-expanded`, reduced-motion; "Pinned Repositories" label was untrue (just most-recent repos); CV is only a button + JS blob |

## 2. Changes (files)
Modified: `index.html`, `style.css`, `main.js` · Added: `assets/Mustafa_Mahmoud_CV.pdf` (**byte-identical** to the old Base64 CV, same SHA-256), `assets/photo.jpg` (renamed — it was a JPEG named .png), `assets/og-image.png` (1200×630, from your photo + name), `assets/fonts/*` (4 woff2 + OFL licences + 2.7 KB icon subset), `robots.txt`, `sitemap.xml`, `vercel.json` (cache + nosniff + referrer headers only), `docs/unverified-projects.html`, `docs/REPORT.md`, `README.md`, `tests/regression.py`, `scripts/check-links.mjs` · Removed: `assets/cv.js`, the contribution-graph code/CSS.

## 3. Significant code changes
- **GitHub (FV):** no simulated numbers. Four *verified* repos are static HTML cards (work with JS off / API down); the API only adds stars, "updated" dates and a language share computed from your real repos. 403/network failure → honest note, "—" stats, no invented values. 10-min `sessionStorage` cache avoids rate limits; 8 s timeout.
- **timeAgo (FV):** minutes → hours → days → weeks → months → years; invalid/`null` → `''`; far-future → `''`. 16 boundary cases pass, including day 29/30/31, 364/365.
- **Single source of truth (FV):** hero/About numbers are counted from `data-*` attributes on the content itself.
- **Mobile nav (FV):** `aria-expanded/controls`, label toggles, Escape returns focus, outside click and resize-to-desktop close it.
- **Form (FV with mocked endpoint):** visible labels, autocomplete, inline errors with `aria-invalid/describedby`, focus to first error, `role=status` messages, honeypot, 15 s timeout, failure keeps the typed text and offers email/WhatsApp. Provider unchanged.
- **Performance:** loader hides at DOMContentLoaded; cursor ring and canvas only run when useful (fine pointer, visible, motion allowed; touch gets one static frame); one rAF-throttled scroll handler; debounced resize; tab-hidden pause; hero photo preloaded, `fetchpriority=high`, sized; hero photo no longer starts at `opacity:0` (browsers skip those for LCP).
- **Layout:** correct selectors, larger hero photo on mobile (230–280 px instead of a dead rule), chips kept visible on mobile, `overflow-x:hidden` removed from html/body/sections; glows are clipped inside `#hero`.

## 4. Content decisions I made (please review)
Primary identity "Frontend Developer | React.js"; skills heading "Technologies I Work With"; removed "AI & Full-Stack", "master", "production-quality", "intelligent web applications", "70 %", "I reply within 24 hours" (not provable). Furniture card now HTML/CSS/JS/Bootstrap with README-backed features. Added **Tawasol** (your real React 19 + Router + Supabase repo, "DEPI 2025") because it is the only verifiable React project. About photo replaced by three content cards.

## 5. Requires your input (OWNER)
1. **Formspree form ID** — until replaced the form shows the failure message (email/WhatsApp fallback). *Critical.*
2. **Analytics Dashboard, AI Task Automator, Real Estate Listings** — no repo found. Parked in `docs/unverified-projects.html`, not shown. Give me repo/demo URLs or confirm they should stay hidden.
3. **NTI entry** says "Frontend Developer… real deliverables" but your repos are described "Web Design Summer Training – NTI" (HTML). Confirm the real title/dates; ITI and NTI are both "Present".
4. **Language levels**: I attached Native→Arabic, Professional→English, Conversational→Russian by badge order. Confirm.
5. **LinkedIn**: site uses `/in/moustafawebdevelopment`, CV uses `/in/moustafaweb`. Which is right?
6. **CV is out of date vs the site**: says DEPI "Present", no NTI/ITI/EGX. I did not touch the content.
7. **Live URLs** (Furniture on Vercel, Seif on GitHub Pages) — unreachable from my sandbox. Run `node scripts/check-links.mjs`; if either is down, change its badge.
8. **Tawasol**: live demo? your role? any features worth stating? "Looking for… freelance" line OK?
9. Counts now show 4 trainings, 5 completed courses (original claimed 5 and 7+/8+); confirm what you want counted.
10. Other repos you may want featured: `Marvello_Store`, `fasfoor-project`, `Todo-App`.
11. Real contribution graph: needs a token (can't be in frontend) or a third-party image; not added. Say if you want a third-party widget.

## 6. Responsive results (Chromium, executed) 
360 / 390 / 768 / 1200 / 1440 px: `scrollWidth == clientWidth`, programmatic horizontal scroll stays 0, hero chips inside viewport, no console errors, no failing local assets — with `overflow-x` no longer hidden. Screenshots: `docs/screenshots/`. Not tested: Safari/Firefox, real phones.

## 7. Accessibility
Verified by script: skip link first in tab order and off-screen otherwise, `<main>`, one `<h1>` with no skipped heading levels, labels for every field, alt on every image, placeholder 6.3 : 1, touch targets ≥ 24 px (inline sentence link exempt), reduced-motion behaviour, menu keyboard behaviour, native cursor on touch. Lighthouse accessibility 95 → 100 (automated checks only). **Not done:** screen-reader testing, axe/WAVE, full WCAG 2.2 audit — so no compliance claim.

## 8. Performance (lab only — local server, Lighthouse simulated throttling, headless Chromium; **not** field data, INP not measurable)
| | Before | After |
|---|---|---|
| Mobile performance score | 59 | 84–88 (3 runs) |
| Mobile TBT | 2 310 ms | 110–210 ms |
| Mobile LCP (simulated slow 4G) | 3.5 s | 3.2–3.3 s — **target 2.5 s not met in lab** |
| Mobile CLS | 0 | 0.015 (≤ 0.1) |
| Desktop performance / LCP / CLS | 98 / 0.9 s / 0.001 | 99 / 0.9 s / 0.002 |
| JavaScript shipped | 109 KB | 27 KB |
| Icon font | 1.5 MB (full Devicon) | 2.7 KB (11 glyphs) |
| Third-party hosts at load | Google Fonts ×2, jsDelivr | none (only api.github.com) |
Caveats: my sandbox blocks Google Fonts/jsDelivr, so the "before" run never downloaded them; real "before" was heavier. The test server doesn't gzip (style.css 65 KB raw ≈ 12 KB on Vercel). Remaining mobile LCP delay is render delay from the render-blocking stylesheet and blur effects under 4× CPU throttling.

## 9. SEO (executed checks)
Canonical, `og:url`, `og:image` and JSON-LD all use the Vercel domain; `summary_large_image`; description 154 chars; `robots.txt`, `sitemap.xml`; `og-image.png` is 1200×630; JSON-LD parses as valid JSON (ProfilePage → Person, only facts on the page). Lighthouse SEO 100. Not run: Rich Results/Schema validator, social-card debuggers (need the deployed URL). No ranking promises.

## 10. Regression
`python3 tests/regression.py` → **54/54 passed** (responsive ×5 viewports, timeAgo, honesty checks, GitHub success/403/offline, menu, keyboard/landmarks, form validation/success/failure with mocked endpoint, CV is a real PDF, anchors, loader, touch cursor, touch targets, reduced motion, SEO). Console errors in Lighthouse come from GitHub's 403 on the shared sandbox IP — the exact failure path the page now handles.

## 11. Remaining technical debt
No build/minify step (CSS 58 KB with many inline `style=""`); possible unused CSS; photo could be resized/WebP; `* {min-width:0}` hack at ≤640 px; no CSP; typed-text effect and hero blur effects are the heaviest remaining mobile work.

## 12. Production readiness
Safe to deploy after item 1 (Formspree ID) and 7 (live-link check); items 2–6 are credibility decisions, not blockers.
