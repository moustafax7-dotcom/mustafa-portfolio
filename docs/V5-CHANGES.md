# Portfolio V5 — change log (for review before committing)

## Content
- **Seif's Portfolio** → Live Demo is now `https://seif-portfolio-nine.vercel.app/` (button, clickable screenshot, browser-bar URL); "GitHub Pages" text/tag replaced by Vercel. Screenshot file unchanged.
- **Projects** (existing section, no new section/filters): Furniture → Seif → Tawasol → **Power BI Sales Dashboard** → **Adidas Global Sales & Financial Performance Dashboard**. The two analytics cards link to their real GitHub repos (no live demo exists). Descriptions/tags come from each repo's README.
- **Certificates** 7 → 9: ITI *Web Development using React* (144 hrs, 12 Jul – 22 Aug 2026) and DataCamp *Introduction to SQL* (2 hrs, 30 Oct 2025). Order: DEPI → ITI → NTI → ITIDA Gigs → DataCamp SQL → Huawei → workshops → olympiad. Categories/filters/viewer unchanged. Counters are derived from the DOM/JSON.
- **Games**: Bug Hunter removed (module, tab, CSS, loader code). Sushi Bounce is the only game; the Playground has a single panel and no tabs.

## Fixes found while testing
- Certificate viewer: tapping *Next* on a phone while a **portrait** scan (ITI) was shown closed the viewer (the backdrop-click handler measured the dialog after it had resized). Fixed in `main.js`; the dialog also keeps a steadier height on phones (`assets/sections.css`).
- Project screenshots use each image's own aspect ratio (`--ar`), so nothing is cropped.

## Assets added
`assets/projects/powerbi-sales-dashboard.webp`, `assets/projects/adidas-sales-dashboard.webp` (Excel sheet-tab bar trimmed, dashboard untouched), `assets/certificates/iti-web-development-react{,-thumb}.jpg`, `assets/certificates/datacamp-introduction-to-sql{,-thumb}.jpg`.

## Tests
`tests/_launch.py` lets every test run with `CHROMIUM_PATH=/path/to/chrome`. Bug Hunter checks were replaced by checks that it is gone and that Sushi Bounce / the Playground still work; new checks cover project order, links, screenshots, certificate order and metadata.

## Review locally
    npx serve .            # or: python3 -m http.server 8000   → http://localhost:8000
Then check: Projects at 360/390/768/1024/1440 px, certificate viewer (open ITI on a phone-size window and press Next), Sushi Bounce (keyboard, mouse, touch), and open the Seif demo URL.
