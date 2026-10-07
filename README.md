# Mustafa Mahmoud — Portfolio

Dark, animated developer portfolio built with vanilla HTML, CSS, and JavaScript.
No frameworks, no build step — open the folder and run.

## Project Structure

```
mustafa-portfolio/
├── index.html          Markup only — sections, no inline styles/scripts
├── style.css           All styling, organized into 18 labeled sections
├── main.js             All behavior, organized into 12 labeled sections
├── README.md            This file
└── assets/
    ├── cv.js            CV PDF, base64-encoded, loaded before main.js
    └── photo.png         Profile photo
```

## Running Locally

Browsers block local scripts opened via `file://`, so use a local server:

**VS Code (recommended)**
1. Install the "Live Server" extension (Ritwick Dey)
2. Right-click `index.html` → "Open with Live Server"

**Node**
```bash
npx serve .
```

**Python**
```bash
python -m http.server 5500
```

## Updating the CV

1. Encode your new PDF at https://base64.guru/converter/encode/pdf
2. Copy the output string
3. Open `assets/cv.js` and replace the value assigned to `CV_B64`
4. Save — no other file needs to change

## Deploying to GitHub Pages

Push the contents of this folder to your repository root, then enable
GitHub Pages under **Settings → Pages → Source → main branch / root**.

Live at: https://moustafax7-dotcom.github.io/mustafa-portfolio/

## Sections

| Section    | ID            |
|------------|---------------|
| Hero       | `#hero`       |
| About      | `#about`      |
| Education  | `#education`  |
| Skills     | `#skills`     |
| Projects   | `#projects`   |
| GitHub     | `#github`     |
| Experience | `#experience` |
| Contact    | `#contact`    |
