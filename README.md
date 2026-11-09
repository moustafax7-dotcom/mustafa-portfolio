# Mustafa Mahmoud — Portfolio

Static site: plain HTML, CSS and JavaScript (no framework, no build step).
Production: https://mustafa-portfolio-lyart.vercel.app/

## Run locally
    python3 -m http.server 8000      # then open http://localhost:8000

## Things you edit most
| What | Where |
|---|---|
| CV | replace `assets/Mustafa_Mahmoud_CV.pdf` (keep the file name) |
| Featured repos in the GitHub section | the `.repo-card[data-repo]` blocks in `index.html` (stars/dates are filled from the API) |
| Contact form endpoint | `action` attribute of `<form id="cform">` in `index.html` (currently `https://formspree.io/f/moustafa` — replace with your real Formspree form ID) |
| Hero / About numbers | derived automatically from `data-project`, `data-status`, `data-training`, `data-credential`, `data-language` attributes |
| GitHub calendar | `api/github-contributions.js` needs `GITHUB_TOKEN` (+ optional `GITHUB_USERNAME`) in Vercel — see `docs/github-setup.md` |
| Hide repos from the live list | `HIDDEN_REPOS` at the top of the GitHub section in `main.js` |
| Certificates | add images to `assets/certificates/`, add an entry to `data/certificates.json`, run `node scripts/build-certificates.mjs` |
| Game tuning | constants at the top of `games/sushi-bounce.js` (all values come from the reference source, see docs/REPORT.md §A) |
| Projects not shown yet | `docs/unverified-projects.html` (move a card into the projects grid once its repo/demo is confirmed) |

## Checks
    pip install playwright && playwright install chromium
    # no bundled browser? point the tests at any Chromium/Chrome:  CHROMIUM_PATH=/path/to/chrome python3 tests/features.py
    # optional: SHOTS_DIR=/tmp/shots (screenshots) and PERF_OUT=/tmp/perf.json keep docs/ untouched
    # no bundled browser available? point the tests at any Chrome/Chromium:  CHROMIUM_PATH=/path/to/chrome python3 tests/features.py
    # SHOTS_DIR=/tmp/shots keeps screenshots out of docs/screenshots; PERF_OUT=/tmp/perf.json keeps perf numbers out of docs/
    python3 tests/regression.py          # 51 checks, mocks GitHub + Formspree, sends nothing real
    python3 tests/features.py            # certificates, projects, Playground (Bug Hunter removed), Sushi Bounce (verified mechanics), responsive
    python3 tests/perf.py                # 15 checks: main-thread budgets, laziness, interaction + frame timing (writes docs/perf-results.json)
    python3 tests/github.py              # 43 checks: GitHub section + contribution calendar (real fixtures, mocked network)
    node --test tests/api.test.mjs       # 11 checks: the serverless function
    node scripts/verify-contributions.mjs <site-url>   # compare the live calendar with github.com
    node scripts/check-links.mjs         # verifies every external link (run on your own network)

## Credits
Fonts: Geist, Geist Mono, Instrument Serif (SIL OFL 1.1, see `assets/fonts/LICENSE-*.txt`).
Icons: subset of Devicon v2.17.0 (MIT).
