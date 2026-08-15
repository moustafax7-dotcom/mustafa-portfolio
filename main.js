/**
 * Mustafa Mahmoud — Portfolio
 * main.js
 * ---------------------------------------------------------------------------
 * Loaded after assets/cv.js (which defines the global CV_B64 constant).
 *
 * Sections:
 *   0. Fail-safe error handler
 *   1. Custom cursor
 *   2. Mobile navigation
 *   3. Hero canvas (interactive dot field)
 *   4. Typed role text
 *   5. Scroll-reveal animations
 *   6. CV download
 *   7. GitHub API (profile + repos)
 *   8. Contribution graph
 *   9. Contact form
 *   10. Page loader
 *   11. Active nav link on scroll
 *   12. Scroll-to-top button
 * ---------------------------------------------------------------------------
 */

/* ==========================================================================
   0. FAIL-SAFE: reveal all content if any script above throws
   ========================================================================== */

// If any later section of this file throws an uncaught error, the
// IntersectionObserver in section 5 may never run, permanently leaving
// .reveal elements at opacity:0 (see html.js .reveal in style.css). This
// listener guarantees content becomes visible even if that happens.
window.addEventListener('error', () => {
  document.querySelectorAll('.reveal').forEach((el) => el.classList.add('in'));
});

/* ==========================================================================
   1. CUSTOM CURSOR
   ========================================================================== */

const cursorRing = document.getElementById('cur-r');
const cursorDot = document.getElementById('cur-d');

let mouseX = 0, mouseY = 0;
let ringX = 0, ringY = 0;

document.addEventListener('mousemove', (e) => {
  mouseX = e.clientX;
  mouseY = e.clientY;
  cursorDot.style.left = `${mouseX}px`;
  cursorDot.style.top = `${mouseY}px`;
});

function animateCursorRing() {
  ringX += (mouseX - ringX) * 0.11;
  ringY += (mouseY - ringY) * 0.11;
  cursorRing.style.left = `${ringX}px`;
  cursorRing.style.top = `${ringY}px`;
  requestAnimationFrame(animateCursorRing);
}
animateCursorRing();

const HOVER_TARGETS = 'a, button, .proj-card, .cert-card, .exp-card, .sk-card, .repo-card, .edu-card, .social-icon';

// Event delegation via bubbling `mouseover`/`mouseout` (unlike `mouseenter`/`mouseleave`,
// these bubble to `document`), so this also covers elements added to the DOM later —
// such as GitHub repo cards, which are fetched and inserted asynchronously.
document.addEventListener('mouseover', (e) => {
  if (e.target.closest(HOVER_TARGETS)) {
    cursorRing.style.width = '52px';
    cursorRing.style.height = '52px';
    cursorRing.style.borderColor = 'rgba(79,142,247,.8)';
  }
});

document.addEventListener('mouseout', (e) => {
  const target = e.target.closest(HOVER_TARGETS);
  // relatedTarget is where the pointer is going; skip if still inside the same target
  if (target && !target.contains(e.relatedTarget)) {
    cursorRing.style.width = '38px';
    cursorRing.style.height = '38px';
    cursorRing.style.borderColor = 'rgba(79,142,247,.45)';
  }
});


/* ==========================================================================
   2. MOBILE NAVIGATION
   ========================================================================== */

const hamburgerBtn = document.getElementById('ham');
const mobileMenu = document.getElementById('mob-menu');
const navBar = document.getElementById('nav');

hamburgerBtn.addEventListener('click', () => {
  hamburgerBtn.classList.toggle('open');
  mobileMenu.classList.toggle('show');
});

function closeMobileMenu() {
  hamburgerBtn.classList.remove('open');
  mobileMenu.classList.remove('show');
}

// Close the mobile menu whenever a nav link inside it is clicked
mobileMenu.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', closeMobileMenu);
});

window.addEventListener(
  'scroll',
  () => navBar.classList.toggle('solid', window.scrollY > 50),
  { passive: true }
);


/* ==========================================================================
   3. HERO CANVAS — INTERACTIVE DOT FIELD
   ========================================================================== */

const heroCanvas = document.getElementById('hcanvas');
const heroCtx = heroCanvas.getContext('2d');

let canvasWidth, canvasHeight;
let dots = [];
let pointerX = 0, pointerY = 0;
let elapsedTime = 0;

const DOT_SPACING = 52;
const REPEL_RADIUS = 150;
const REPEL_STRENGTH = 10;

function initHeroCanvas() {
  canvasWidth = heroCanvas.width = window.innerWidth;
  canvasHeight = heroCanvas.height = window.innerHeight;

  dots = [];
  for (let x = 0; x < canvasWidth + DOT_SPACING; x += DOT_SPACING) {
    for (let y = 0; y < canvasHeight + DOT_SPACING; y += DOT_SPACING) {
      dots.push({
        x, y,
        originX: x,
        originY: y,
        radius: Math.random() * 1.8 + 0.5,
        phase: Math.random() * Math.PI * 2,
        speed: Math.random() * 0.4 + 0.2,
      });
    }
  }

  pointerX = canvasWidth / 2;
  pointerY = canvasHeight / 2;
}

function drawHeroCanvas() {
  heroCtx.clearRect(0, 0, canvasWidth, canvasHeight);
  elapsedTime += 0.008;

  dots.forEach((dot) => {
    const wave = Math.sin(elapsedTime * dot.speed + dot.phase) * 0.6;

    const dx = dot.originX - pointerX;
    const dy = dot.originY - pointerY;
    const distance = Math.sqrt(dx * dx + dy * dy) || 1;
    const repelForce = Math.max(0, 1 - distance / REPEL_RADIUS) * REPEL_STRENGTH;

    dot.x = dot.originX + (dx / distance) * repelForce;
    dot.y = dot.originY + (dy / distance) * repelForce;

    const opacity = 0.12 + repelForce * 0.05 + wave * 0.04;

    heroCtx.beginPath();
    heroCtx.arc(dot.x, dot.y, dot.radius, 0, Math.PI * 2);
    heroCtx.fillStyle = `rgba(79,142,247,${opacity})`;
    heroCtx.fill();
  });

  if (isHeroVisible) {
    canvasAnimationId = requestAnimationFrame(drawHeroCanvas);
  } else {
    canvasAnimationId = null;
  }
}

window.addEventListener('mousemove', (e) => {
  pointerX = e.clientX;
  pointerY = e.clientY;
});
window.addEventListener('resize', initHeroCanvas);

// Pause the animation loop while the hero section is scrolled out of view —
// with hundreds to thousands of dots on large screens, redrawing every frame
// indefinitely (even off-screen) wastes CPU/GPU for no visible benefit.
let isHeroVisible = true;
let canvasAnimationId = null;

new IntersectionObserver(
  ([entry]) => {
    isHeroVisible = entry.isIntersecting;
    if (isHeroVisible && canvasAnimationId === null) {
      drawHeroCanvas();
    }
  },
  { threshold: 0 }
).observe(document.getElementById('hero'));

initHeroCanvas();
drawHeroCanvas();


/* ==========================================================================
   4. TYPED ROLE TEXT
   ========================================================================== */

const typedTextEl = document.getElementById('typed');

const ROLES = [
  'Frontend React Developer',
  'AI & Full-Stack Developer',
  'UI/UX Enthusiast',
  'Open to Opportunities',
];

const TYPE_SPEED = 62;
const DELETE_SPEED = 38;
const HOLD_DURATION = 2000;
const PAUSE_BEFORE_NEXT = 350;

let roleIndex = 0;
let charIndex = 0;
let isDeleting = false;

function typeNextCharacter() {
  const currentRole = ROLES[roleIndex];

  if (!isDeleting) {
    typedTextEl.textContent = currentRole.slice(0, ++charIndex);

    if (charIndex === currentRole.length) {
      isDeleting = true;
      setTimeout(typeNextCharacter, HOLD_DURATION);
      return;
    }
  } else {
    typedTextEl.textContent = currentRole.slice(0, --charIndex);

    if (charIndex === 0) {
      isDeleting = false;
      roleIndex = (roleIndex + 1) % ROLES.length;
      setTimeout(typeNextCharacter, PAUSE_BEFORE_NEXT);
      return;
    }
  }

  setTimeout(typeNextCharacter, isDeleting ? DELETE_SPEED : TYPE_SPEED);
}

setTimeout(typeNextCharacter, 1200);


/* ==========================================================================
   5. SCROLL-REVEAL ANIMATIONS
   ========================================================================== */

const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add('in');
    });
  },
  { threshold: 0.08 }
);

document.querySelectorAll('.reveal').forEach((el) => revealObserver.observe(el));


/* ==========================================================================
   6. CV DOWNLOAD
   ========================================================================== */

const spinKeyframes = document.createElement('style');
spinKeyframes.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
document.head.appendChild(spinKeyframes);

document.getElementById('cvBtn').addEventListener('click', function downloadCV() {
  const button = this;
  const originalHTML = button.innerHTML;

  button.innerHTML = `
    <svg class="cv-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2" style="animation:spin .7s linear infinite">
      <path d="M21 12a9 9 0 1 1-6.22-8.56"/>
    </svg>
    <span class="cv-txt"> Preparing...</span>`;
  button.disabled = true;

  setTimeout(() => {
    try {
      const binary = atob(CV_B64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }

      const blobUrl = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = 'Mustafa_Mahmoud_CV.pdf';

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);

      button.innerHTML = `
        <svg class="cv-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2.5">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span class="cv-txt"> Downloaded ✓</span>`;
      button.style.borderColor = 'rgba(52,211,153,.6)';
      button.style.color = 'var(--green)';
    } catch (err) {
      // CV_B64 is malformed (e.g. corrupted paste when updating assets/cv.js) — fail visibly
      // instead of leaving the button stuck on "Preparing..." forever.
      console.error('CV download failed — CV_B64 may be corrupted:', err);
      button.innerHTML = originalHTML.replace('Download CV', 'Download failed');
      button.style.borderColor = 'rgba(239,68,68,.6)';
      button.style.color = '#ef4444';
    }

    setTimeout(() => {
      button.innerHTML = originalHTML;
      button.disabled = false;
      button.style.borderColor = '';
      button.style.color = '';
    }, 2400);
  }, 650);
});


/* ==========================================================================
   7. GITHUB API — PROFILE & REPOS
   ========================================================================== */

const GITHUB_USERNAME = 'moustafax7-dotcom';

const LANGUAGE_COLORS = {
  JavaScript: '#f1e05a',
  Python: '#3776ab',
  HTML: '#e34c26',
  CSS: '#563d7c',
  TypeScript: '#3178c6',
};

const FALLBACK_REPOS = [
  { name: 'ecommerce-react', desc: 'Full-featured store with React.js and REST API.', lang: 'JavaScript', stars: 3, updated: '2 days ago' },
  { name: 'analytics-dashboard', desc: 'Real-time dashboard with Chart.js and dark mode.', lang: 'JavaScript', stars: 5, updated: '1 week ago' },
  { name: 'ai-task-automator', desc: 'Python automation tool using AI APIs.', lang: 'Python', stars: 2, updated: '2 weeks ago' },
  { name: 'portfolio', desc: 'Personal portfolio — fast, responsive, modern.', lang: 'HTML', stars: 4, updated: '3 days ago' },
];

function starIconSVG() {
  return `<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
  </svg>`;
}

function buildRepoCard({ url, name, stars, description, language, updatedLabel }) {
  const color = LANGUAGE_COLORS[language] || '#8b8fa8';

  const card = document.createElement('a');
  card.href = url;                 // safe: DOM property assignment, not string concatenation
  card.target = '_blank';
  card.rel = 'noopener noreferrer';
  card.className = 'repo-card';

  const top = document.createElement('div');
  top.className = 'repo-top';

  const nameEl = document.createElement('span');
  nameEl.className = 'repo-name';
  nameEl.textContent = name;       // safe: textContent never parses HTML

  const starsEl = document.createElement('span');
  starsEl.className = 'repo-stars';
  starsEl.innerHTML = starIconSVG(); // safe: fixed, hardcoded markup — no external data here
  starsEl.append(document.createTextNode(String(stars)));

  top.append(nameEl, starsEl);

  const descEl = document.createElement('div');
  descEl.className = 'repo-desc';
  descEl.textContent = description || 'No description.';

  const meta = document.createElement('div');
  meta.className = 'repo-meta';

  if (language) {
    const langEl = document.createElement('span');
    langEl.className = 'repo-lang';

    const dot = document.createElement('span');
    dot.className = 'repo-ldot';
    dot.style.background = color;

    langEl.append(dot, document.createTextNode(language));
    meta.appendChild(langEl);
  }

  const updEl = document.createElement('span');
  updEl.className = 'repo-upd';
  updEl.textContent = `Updated ${updatedLabel}`;
  meta.appendChild(updEl);

  card.append(top, descEl, meta);
  return card;
}

function timeAgo(date) {
  const seconds = Math.floor((Date.now() - date) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hr ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;
  return `${Math.floor(seconds / 2592000)} months ago`;
}

function renderDefaultRepos() {
  const container = document.getElementById('repos-list');
  container.innerHTML = ''; // clear any previous content
  FALLBACK_REPOS.forEach((repo) => {
    container.appendChild(
      buildRepoCard({
        url: `https://github.com/${GITHUB_USERNAME}/${repo.name}`,
        name: repo.name,
        stars: repo.stars,
        description: repo.desc,
        language: repo.lang,
        updatedLabel: repo.updated,
      })
    );
  });
}

fetch(`https://api.github.com/users/${GITHUB_USERNAME}`)
  .then((res) => res.json())
  .then((user) => {
    document.getElementById('gh-repos').textContent = user.public_repos ?? '—';
    document.getElementById('gh-follow').textContent = user.followers ?? '—';
    document.getElementById('gh-fing').textContent = user.following ?? '—';
  })
  .catch(() => {
    /* API unavailable — stats remain at their placeholder value */
  });

fetch(`https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated&per_page=4`)
  .then((res) => res.json())
  .then((repos) => {
    if (!Array.isArray(repos) || repos.length === 0) {
      renderDefaultRepos();
      return;
    }

    const container = document.getElementById('repos-list');
    container.innerHTML = ''; // clear any previous content

    repos.slice(0, 4).forEach((repo) => {
      container.appendChild(
        buildRepoCard({
          url: repo.html_url,
          name: repo.name,
          stars: repo.stargazers_count,
          description: repo.description,
          language: repo.language,
          updatedLabel: timeAgo(new Date(repo.updated_at)),
        })
      );
    });
  })
  .catch(renderDefaultRepos);


/* ==========================================================================
   8. CONTRIBUTION GRAPH (SIMULATED)
   ========================================================================== */

(function renderContributionGraph() {
  const grid = document.getElementById('contrib-grid');
  const monthsRow = document.getElementById('contrib-months');
  const now = new Date();

  const WEEKS = 52;
  const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  let totalContributions = 0;

  const monthLabels = [];
  for (let week = 0; week < WEEKS; week += 4) {
    const date = new Date(now);
    date.setDate(date.getDate() - (WEEKS - week) * 7);
    monthLabels.push(MONTH_NAMES[date.getMonth()]);
  }
  monthsRow.innerHTML = monthLabels
    .map((label) => `<span class="contrib-mo" style="flex:4">${label}</span>`)
    .join('');

  // Deterministic activity pattern: later weeks trend busier, weekends quieter
  for (let week = 0; week < WEEKS; week++) {
    const column = document.createElement('div');
    column.className = 'contrib-col';

    for (let day = 0; day < 7; day++) {
      const cell = document.createElement('div');
      const seed = ((week * 7 + day) * 2654435761) >>> 0;

      const recencyBoost = week > 40 ? 0.25 : week > 30 ? 0.15 : 0;
      const weekendPenalty = day === 0 || day === 6 ? -0.2 : 0;
      const activityChance = 0.55 + recencyBoost + weekendPenalty;

      const isActive = (seed % 100) / 100 < activityChance;

      if (!isActive) {
        cell.className = 'contrib-cell level-0';
      } else {
        const level = (seed % 100) < 20 ? 4 : (seed % 100) < 45 ? 3 : (seed % 100) < 70 ? 2 : 1;
        cell.className = `contrib-cell level-${level}`;
        totalContributions += level;
      }

      const cellDate = new Date(now);
      cellDate.setDate(cellDate.getDate() - (WEEKS - week) * 7 + day);
      const contributionCount = isActive ? (seed % 5) + 1 : 0;
      cell.title = `${cellDate.toDateString()} · ${contributionCount} contributions`;

      column.appendChild(cell);
    }

    grid.appendChild(column);
  }

  document.getElementById('contrib-total').textContent =
    `${totalContributions} contributions in the last year`;
})();


/* ==========================================================================
   9. CONTACT FORM
   ========================================================================== */

document.getElementById('cform').addEventListener('submit', async function handleContactSubmit(e) {
  e.preventDefault();

  const submitButton = this.querySelector('.f-btn');
  const originalHTML = submitButton.innerHTML;

  submitButton.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2" style="animation:spin .7s linear infinite">
      <path d="M21 12a9 9 0 1 1-6.22-8.56"/>
    </svg> Sending...`;
  submitButton.disabled = true;

  const formData = new FormData(this);

  try {
    // NOTE: replace 'moustafa' with your real Formspree form ID
    // (sign up free at https://formspree.io — the ID is in your dashboard URL)
    const response = await fetch('https://formspree.io/f/moustafa', {
      method: 'POST',
      body: formData,
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) throw new Error('Form submission failed');

    this.innerHTML = `
      <div class="f-ok">
        <div class="f-ok-ico">✅</div>
        <p>Message sent!<br/>I'll reply within 24 hours.</p>
      </div>`;
  } catch {
    submitButton.innerHTML = originalHTML;
    submitButton.disabled = false;
    submitButton.style.background = 'rgba(239,68,68,.8)';
    submitButton.textContent = 'Failed — try WhatsApp instead';

    setTimeout(() => {
      submitButton.innerHTML = originalHTML;
      submitButton.disabled = false;
      submitButton.style.background = '';
    }, 3000);
  }
});


/* ==========================================================================
   10. PAGE LOADER
   ========================================================================== */

window.addEventListener('load', () => {
  setTimeout(() => {
    const loader = document.getElementById('loader');
    if (!loader) return;

    loader.classList.add('hidden');
    setTimeout(() => loader.remove(), 600);
  }, 800);
});


/* ==========================================================================
   11. ACTIVE NAV LINK ON SCROLL
   ========================================================================== */

(function highlightActiveNavLink() {
  const sectionIds = ['hero', 'about', 'education', 'skills', 'projects', 'github', 'experience', 'contact'];
  const navLinks = document.querySelectorAll('.n-links a');

  const sectionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;

        const activeId = entry.target.id;
        navLinks.forEach((link) => {
          link.classList.toggle('active', link.getAttribute('href') === `#${activeId}`);
        });
      });
    },
    { threshold: 0.35, rootMargin: '-60px 0px -40% 0px' }
  );

  sectionIds.forEach((id) => {
    const section = document.getElementById(id);
    if (section) sectionObserver.observe(section);
  });
})();


/* ==========================================================================
   12. SCROLL-TO-TOP BUTTON
   ========================================================================== */

(function initScrollToTopButton() {
  const button = document.getElementById('stt');

  window.addEventListener(
    'scroll',
    () => button.classList.toggle('show', window.scrollY > 400),
    { passive: true }
  );

  button.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();
