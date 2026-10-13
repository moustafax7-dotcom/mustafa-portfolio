/**
 * Mustafa Mahmoud — Portfolio
 * main.js
 * ---------------------------------------------------------------------------
 * Sections:
 *   0. Helpers + fail-safe
 *   1. Custom cursor (fine pointers only)
 *   2. Mobile navigation (accessible)
 *   3. Hero canvas (interactive dot field)
 *   4. Typed role text
 *   5. Scroll-reveal animations
 *   6. Counts derived from the page content
 *   7. GitHub (latest repos, stats, language share, real contribution calendar)
 *   8. Contact form
 *   8b. Certificates gallery + viewer, 8c. Dev Playground (games load on demand)
 *   9. Page loader
 *  10. Active nav link, scroll-linked UI, footer year
 * ---------------------------------------------------------------------------
 */
'use strict';

/* ==========================================================================
   0. HELPERS + FAIL-SAFE
   ========================================================================== */

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

// If any later section throws, make sure .reveal content can never stay at opacity:0.
window.addEventListener('error', () => {
  $$('.reveal').forEach((el) => el.classList.add('in'));
});

/** Run `fn` at most once per animation frame (scroll/resize handlers). */
function rafThrottle(fn) {
  let queued = false;
  return (...args) => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      fn(...args);
    });
  };
}

/* ==========================================================================
   1. CUSTOM CURSOR — only for fine pointers, never with reduced motion
   ========================================================================== */

(function initCustomCursor() {
  const ring = $('#cur-r');
  const dot = $('#cur-d');
  if (!ring || !dot) return;

  // Nothing runs at startup (matchMedia() would force a synchronous style/layout pass during the
  // page's busiest moment). The cursor is set up the first time a real mouse moves.
  let ready = false;
  const arm = (e) => {
    if (e.pointerType !== 'mouse') return;
    window.removeEventListener('pointermove', arm);
    if (!ready) {
      ready = true;
      setup(e);
    }
  };
  window.addEventListener('pointermove', arm, { passive: true });

  function setup(first) {
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');

  const HOVER_TARGETS = 'a, button, .proj-card, .cert-card, .exp-card, .sk-card, .repo-card, .edu-card, .social-icon';
  let mouseX = first.clientX;
  let mouseY = first.clientY;
  let ringX = mouseX;
  let ringY = mouseY;
  let rafId = 0;

  const place = (el, x, y) => {
    el.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`;
  };

  // The ring eases toward the pointer; the loop stops once it has caught up.
  function follow() {
    ringX += (mouseX - ringX) * 0.11;
    ringY += (mouseY - ringY) * 0.11;
    place(ring, ringX, ringY);
    if (Math.abs(mouseX - ringX) > 0.1 || Math.abs(mouseY - ringY) > 0.1) {
      rafId = requestAnimationFrame(follow);
    } else {
      rafId = 0;
    }
  }

  function onMove(e) {
    mouseX = e.clientX;
    mouseY = e.clientY;
    place(dot, mouseX, mouseY);
    if (!rafId) rafId = requestAnimationFrame(follow);
  }

  // Event delegation covers elements added later; mouseover/mouseout bubble.
  function onOver(e) {
    if (e.target.closest(HOVER_TARGETS)) {
      ring.style.width = '52px';
      ring.style.height = '52px';
      ring.style.borderColor = 'rgba(79,142,247,.8)';
    }
  }
  function onOut(e) {
    const target = e.target.closest(HOVER_TARGETS);
    if (target && !target.contains(e.relatedTarget)) {
      ring.style.width = '';
      ring.style.height = '';
      ring.style.borderColor = '';
    }
  }

  function enable() {
    ring.style.left = ring.style.top = dot.style.left = dot.style.top = '0';
    document.documentElement.classList.add('has-cursor');
    document.addEventListener('mousemove', onMove, { passive: true });
    document.addEventListener('mouseover', onOver);
    document.addEventListener('mouseout', onOut);
  }
  function disable() {
    document.documentElement.classList.remove('has-cursor');
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseover', onOver);
    document.removeEventListener('mouseout', onOut);
    cancelAnimationFrame(rafId);
    rafId = 0;
  }

  const sync = () => (finePointer.matches && !reducedMotion.matches ? enable() : disable());
  sync();
  onMove(first); // place the cursor where the mouse already is
  finePointer.addEventListener('change', sync);
  reducedMotion.addEventListener('change', sync);
  }
})();

/* ==========================================================================
   2. MOBILE NAVIGATION
   ========================================================================== */

(function initMobileNavigation() {
  const button = $('#ham');
  const menu = $('#mob-menu');
  if (!button || !menu) return;

  const isOpen = () => menu.classList.contains('show');

  function setOpen(open, { returnFocus = false } = {}) {
    button.classList.toggle('open', open);
    menu.classList.toggle('show', open);
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    if (!open && returnFocus) button.focus();
  }

  button.addEventListener('click', () => setOpen(!isOpen()));

  // Choosing a link closes the menu (the page then scrolls to the section).
  $$('a', menu).forEach((link) => link.addEventListener('click', () => setOpen(false)));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isOpen()) setOpen(false, { returnFocus: true });
  });

  // Tapping outside the menu closes it.
  document.addEventListener('click', (e) => {
    if (isOpen() && !menu.contains(e.target) && !button.contains(e.target)) setOpen(false);
  });

  // The hamburger is only shown on narrow screens; reset if the window grows.
  window.matchMedia('(min-width: 901px)').addEventListener('change', (e) => {
    if (e.matches) setOpen(false);
  });
})();

/* ==========================================================================
   3. HERO CANVAS — INTERACTIVE DOT FIELD
   ========================================================================== */

(function initHeroCanvas() {
  const canvas = $('#hcanvas');
  const hero = $('#hero');
  if (!canvas || !hero) return;

  // Pause every hero animation (CSS) while the hero is off-screen — whatever device this is.
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      document.documentElement.classList.toggle('hero-off', !entry.isIntersecting);
    }).observe(hero);
  }

  // The animated dot field is desktop-only: phones, tablets and touch devices get the static CSS pattern.
  if (!window.matchMedia('(min-width: 901px) and (hover: hover) and (pointer: fine)').matches) return;
  const ctx = canvas.getContext('2d');

  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const DOT_SPACING = 52;
  const REPEL_RADIUS = 150;
  const REPEL_STRENGTH = 10;

  let width = 0;
  let height = 0;
  let dots = [];
  let pointerX = 0;
  let pointerY = 0;
  let elapsed = 0;
  let heroVisible = true;
  let running = false;
  let rafId = 0;

  function build() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    dots = [];
    for (let x = 0; x < width + DOT_SPACING; x += DOT_SPACING) {
      for (let y = 0; y < height + DOT_SPACING; y += DOT_SPACING) {
        dots.push({
          originX: x,
          originY: y,
          radius: Math.random() * 1.8 + 0.5,
          phase: Math.random() * Math.PI * 2,
          speed: Math.random() * 0.4 + 0.2,
        });
      }
    }
    pointerX = width / 2;
    pointerY = height / 2;
    draw(); // always paint once (also the only frame when motion is reduced)
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);
    elapsed += 0.008;

    for (const dot of dots) {
      const wave = Math.sin(elapsed * dot.speed + dot.phase) * 0.6;
      const dx = dot.originX - pointerX;
      const dy = dot.originY - pointerY;
      const distance = Math.hypot(dx, dy) || 1;
      const repel = Math.max(0, 1 - distance / REPEL_RADIUS) * REPEL_STRENGTH;

      ctx.beginPath();
      ctx.arc(dot.originX + (dx / distance) * repel, dot.originY + (dy / distance) * repel, dot.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(79,142,247,${0.12 + repel * 0.05 + wave * 0.04})`;
      ctx.fill();
    }
  }

  function loop() {
    draw();
    rafId = requestAnimationFrame(loop);
  }

  // Animate only while the hero is on screen, the tab is visible and motion is allowed.
  function sync() {
    // Touch devices have no pointer to react to the field, so they get a single static frame.
    const shouldRun = heroVisible && !document.hidden && !reducedMotion.matches && finePointer.matches;
    if (shouldRun && !running) {
      running = true;
      rafId = requestAnimationFrame(loop);
    } else if (!shouldRun && running) {
      running = false;
      cancelAnimationFrame(rafId);
    }
  }

  window.addEventListener(
    'pointermove',
    (e) => {
      if (e.pointerType === 'mouse') {
        pointerX = e.clientX;
        pointerY = e.clientY;
      }
    },
    { passive: true }
  );

  let resizeTimer = 0;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(build, 150);
  });

  document.addEventListener('visibilitychange', sync);
  reducedMotion.addEventListener('change', sync);
  finePointer.addEventListener('change', sync);

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      heroVisible = entry.isIntersecting;
      sync();
    }).observe(hero);
  }

  build();
  sync();
})();

/* ==========================================================================
   4. TYPED ROLE TEXT
   ========================================================================== */

(function initTypedRole() {
  const el = $('#typed');
  if (!el || reducedMotion.matches) return; // the HTML already shows the primary title

  const ROLES = ['Frontend Developer | React.js', 'UI/UX Enthusiast', 'Open to Opportunities'];
  const TYPE_SPEED = 62;
  const DELETE_SPEED = 38;
  const HOLD = 2000;
  const PAUSE = 350;

  let roleIndex = 0;
  let charIndex = ROLES[0].length; // starts on the static text that is already in the HTML
  let deleting = true;

  function step() {
    if (document.hidden || reducedMotion.matches) {
      setTimeout(step, 500);
      return;
    }
    const role = ROLES[roleIndex];

    if (!deleting) {
      el.textContent = role.slice(0, ++charIndex);
      if (charIndex === role.length) {
        deleting = true;
        setTimeout(step, HOLD);
        return;
      }
    } else {
      el.textContent = role.slice(0, --charIndex);
      if (charIndex === 0) {
        deleting = false;
        roleIndex = (roleIndex + 1) % ROLES.length;
        setTimeout(step, PAUSE);
        return;
      }
    }
    setTimeout(step, deleting ? DELETE_SPEED : TYPE_SPEED);
  }

  setTimeout(step, HOLD + 400);
})();

/* ==========================================================================
   5. SCROLL-REVEAL ANIMATIONS
   ========================================================================== */

(function initReveal() {
  const items = $$('.reveal');
  if (reducedMotion.matches || !('IntersectionObserver' in window)) {
    items.forEach((el) => el.classList.add('in'));
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08 }
  );
  items.forEach((el) => observer.observe(el));
})();

/* ==========================================================================
   6. COUNTS DERIVED FROM THE PAGE
   One source of truth: the numbers in the hero and About section are counted
   from the content that is actually displayed, so they cannot drift apart.
   ========================================================================== */

(function renderDerivedCounts() {
  const isShown = (el) => !el.closest('[hidden]');
  const setCount = (name, value) =>
    $$(`[data-count="${name}"]`).forEach((el) => {
      el.textContent = String(value);
    });

  setCount('projects', $$('[data-project]').filter(isShown).length);
  setCount('live', $$('[data-project][data-status="live"]').filter(isShown).length);
  setCount('trainings', $$('[data-training]').length);
  setCount('credentials', $$('.cert-item').length);
  setCount('languages', $$('[data-language]').length);
})();

/* ==========================================================================
   7. GITHUB — latest repositories, profile stats, language share and the
   real contribution calendar. No simulated numbers anywhere: whatever GitHub
   cannot give us is shown as unavailable, never invented.
   Nothing is requested until the section is near the viewport.
   ========================================================================== */

const GITHUB_USERNAME = 'moustafax7-dotcom';
const GITHUB_API = 'https://api.github.com';
const CONTRIBUTIONS_ENDPOINT = '/api/github-contributions';
const GITHUB_CACHE_KEY = 'portfolio:github:v2';
const GITHUB_CACHE_TTL_MS = 30 * 60 * 1000; // fresh for 30 min; older copies are only shown if GitHub cannot be reached
const GITHUB_REPO_LIMIT = 6;
// Repository names to leave out of the "latest repositories" list (case-insensitive). Forks and the
// profile repositories (<username> and <username>.github.io) are always skipped.
const HIDDEN_REPOS = [];

const LANGUAGE_COLORS = {
  JavaScript: '#f1e05a',
  TypeScript: '#3178c6',
  Python: '#3776ab',
  HTML: '#e34c26',
  CSS: '#563d7c',
  'C++': '#f34b7d',
  Java: '#b07219',
  Shell: '#89e051',
  R: '#198ce7',
};
const DEFAULT_LANGUAGE_COLOR = '#8b8fa8';

/**
 * Human-readable relative time.
 * Returns '' for invalid dates and for dates more than 5 minutes in the future,
 * so callers can simply hide the label instead of showing nonsense.
 */
function timeAgo(date, now = Date.now()) {
  if (date === null || date === undefined || date === '') return '';
  const then = date instanceof Date ? date.getTime() : new Date(date).getTime();
  if (!Number.isFinite(then) || !Number.isFinite(now)) return '';

  const seconds = Math.floor((now - then) / 1000);
  if (seconds < -300) return '';
  if (seconds < 60) return 'just now';

  const plural = (n, unit) => `${n} ${unit}${n === 1 ? '' : 's'} ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return plural(days, 'day');
  if (days < 30) return plural(Math.floor(days / 7), 'week');
  if (days < 365) return plural(Math.max(1, Math.floor(days / 30.44)), 'month');
  return plural(Math.max(1, Math.floor(days / 365.25)), 'year');
}

const make = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
};

/* ---------- repositories ---------- */

/**
 * The repositories to show: newest *push* first (pushed_at tracks real development;
 * updated_at also changes when someone stars or edits settings), forks and profile
 * repositories excluded, limited to `limit`.
 */
function selectLatestRepos(repos, { limit = GITHUB_REPO_LIMIT, hidden = HIDDEN_REPOS, username = GITHUB_USERNAME } = {}) {
  if (!Array.isArray(repos)) return [];
  const skip = new Set([...hidden, username, `${username}.github.io`].map((n) => String(n).toLowerCase()));
  const when = (repo) => {
    const t = Date.parse(repo.pushed_at || repo.updated_at || '');
    return Number.isFinite(t) ? t : 0;
  };
  return repos
    .filter((repo) => repo && repo.name && !repo.fork && !skip.has(String(repo.name).toLowerCase()))
    .sort((a, b) => when(b) - when(a))
    .slice(0, limit);
}

async function fetchGitHubJSON(path, timeoutMs = 8000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${GITHUB_API}${path}`, {
      headers: { Accept: 'application/vnd.github+json' },
      signal: controller.signal,
    });
    if (!response.ok) {
      const error = new Error(`GitHub API responded with ${response.status}`);
      error.rateLimited = response.status === 403 || response.status === 429;
      throw error;
    }
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

function readGitHubCache() {
  try {
    const cached = JSON.parse(localStorage.getItem(GITHUB_CACHE_KEY) || 'null');
    if (cached && Number.isFinite(cached.savedAt) && Array.isArray(cached.repos)) return cached;
  } catch {
    /* storage unavailable or corrupt: just fetch again */
  }
  return null;
}

function writeGitHubCache(user, repos) {
  const slim = repos.map((r) => ({
    name: r.name,
    description: r.description,
    language: r.language,
    stargazers_count: r.stargazers_count,
    pushed_at: r.pushed_at,
    updated_at: r.updated_at,
    fork: r.fork,
    html_url: r.html_url,
  }));
  const slimUser = user ? { public_repos: user.public_repos, followers: user.followers, following: user.following } : null;
  try {
    localStorage.setItem(GITHUB_CACHE_KEY, JSON.stringify({ savedAt: Date.now(), user: slimUser, repos: slim }));
  } catch {
    /* storage full or blocked: ignore */
  }
}

function showGitHubNote(message) {
  const note = $('#gh-note');
  if (!note) return;
  note.textContent = message;
  note.hidden = !message;
}

function renderGitHubStats(user) {
  const asCount = (value) => (Number.isFinite(value) ? String(value) : '—');
  const set = (id, value) => {
    const el = $(id);
    if (el) el.textContent = asCount(value);
  };
  set('#gh-repos', user && user.public_repos);
  set('#gh-follow', user && user.followers);
  set('#gh-fing', user && user.following);
}

function buildRepoCard(repo) {
  const card = make('a', 'repo-card');
  card.href = repo.html_url || `https://github.com/${GITHUB_USERNAME}/${encodeURIComponent(repo.name)}`;
  card.target = '_blank';
  card.rel = 'noopener noreferrer';

  const top = make('div', 'repo-top');
  top.append(make('span', 'repo-name', repo.name));
  const stars = Number.isFinite(repo.stargazers_count) ? repo.stargazers_count : null;
  if (stars !== null) {
    const starEl = make('span', 'repo-stars', `★ ${stars}`);
    starEl.setAttribute('aria-label', `${stars} ${stars === 1 ? 'star' : 'stars'}`);
    top.append(starEl);
  }

  // Descriptions are shown exactly as written on GitHub. A missing one is stated, not invented.
  const description = typeof repo.description === 'string' && repo.description.trim() ? repo.description.trim() : '';
  const desc = description ? make('div', 'repo-desc', description) : make('div', 'repo-desc is-empty', 'No description provided');

  const meta = make('div', 'repo-meta');
  const lang = make('span', 'repo-lang');
  if (repo.language) {
    const dot = make('span', 'repo-ldot');
    dot.style.background = LANGUAGE_COLORS[repo.language] || DEFAULT_LANGUAGE_COLOR;
    lang.append(dot, document.createTextNode(repo.language));
  } else {
    lang.textContent = 'No language detected';
  }
  meta.append(lang);

  const pushed = repo.pushed_at || repo.updated_at;
  const relative = timeAgo(pushed);
  if (relative) {
    const upd = make('span', 'repo-upd', `Updated ${relative}`);
    const date = new Date(pushed);
    upd.title = date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    meta.append(upd);
  }

  card.append(top, desc, meta);
  return card;
}

function renderLatestRepos(repos) {
  const live = $('#repos-live');
  const fallback = $('#repos-list');
  const picked = selectLatestRepos(repos);
  if (!live || !picked.length) return false; // nothing to show: keep the static snapshot

  live.replaceChildren(...picked.map(buildRepoCard));
  live.hidden = false;
  if (fallback) fallback.hidden = true;

  const label = $('#repos-lbl');
  if (label) {
    label.replaceChildren('Latest updated repositories ');
    label.append(make('span', 'gh-badge is-live', 'live from GitHub'));
  }
  return true;
}

function renderLanguageShare(repos) {
  const box = $('#langs-box');
  const bar = $('#lang-bar');
  const rows = $('#lang-rows');
  if (!box || !bar || !rows) return;

  // Count primary languages across original (non-fork) repositories.
  const counts = new Map();
  repos
    .filter((repo) => !repo.fork && repo.language)
    .forEach((repo) => counts.set(repo.language, (counts.get(repo.language) || 0) + 1));
  const total = Array.from(counts.values()).reduce((sum, n) => sum + n, 0);
  if (!total) return;

  const top = Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  bar.replaceChildren();
  rows.replaceChildren();

  top.forEach(([language, count]) => {
    const color = LANGUAGE_COLORS[language] || DEFAULT_LANGUAGE_COLOR;
    const segment = make('div', 'lang-seg');
    segment.style.width = `${(count / total) * 100}%`;
    segment.style.background = color;
    bar.appendChild(segment);

    const row = make('div', 'lang-row');
    const name = make('span', 'lang-name');
    const dot = make('span', 'lang-dot');
    dot.style.background = color;
    name.append(dot, document.createTextNode(language));
    row.append(name, make('span', 'lang-pct', `${Math.round((count / total) * 100)}%`));
    rows.appendChild(row);
  });

  box.hidden = false;
}

function renderGitHubData(data) {
  renderGitHubStats(data.user);
  renderLatestRepos(data.repos);
  renderLanguageShare(data.repos);
}

async function loadGitHubData() {
  const cached = readGitHubCache();
  if (cached && Date.now() - cached.savedAt < GITHUB_CACHE_TTL_MS) {
    renderGitHubData(cached);
    showGitHubNote('');
    return;
  }

  try {
    const [user, repos] = await Promise.all([
      fetchGitHubJSON(`/users/${GITHUB_USERNAME}`),
      fetchGitHubJSON(`/users/${GITHUB_USERNAME}/repos?per_page=100&sort=pushed&direction=desc`),
    ]);
    if (!Array.isArray(repos) || !user || typeof user !== 'object') throw new Error('Unexpected GitHub response');
    writeGitHubCache(user, repos);
    renderGitHubData({ user, repos });
    showGitHubNote('');
  } catch (error) {
    const reason =
      navigator.onLine === false ? 'you appear to be offline' : error && error.rateLimited ? 'GitHub’s request limit was reached' : 'GitHub could not be reached';
    if (cached) {
      renderGitHubData(cached); // stale but real: clearly labelled
      showGitHubNote(`Live update failed (${reason}). Showing GitHub data saved ${timeAgo(cached.savedAt)}.`);
    } else {
      renderGitHubStats(null);
      showGitHubNote(`Live GitHub data is unavailable (${reason}). The repository links above are a verified snapshot, without live stats.`);
    }
  }
}

/* ---------- contribution calendar ---------- */

const WEEKDAY_ROW_LABELS = ['', 'Mon', '', 'Wed', '', 'Fri', ''];
const MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const longDate = new Intl.DateTimeFormat('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' });

const utcParts = (iso) => {
  const d = new Date(`${iso}T00:00:00Z`);
  return { weekday: d.getUTCDay(), month: d.getUTCMonth(), date: d };
};

const contributionLabel = (count, iso) =>
  `${count === 0 ? 'No contributions' : `${count} ${count === 1 ? 'contribution' : 'contributions'}`} on ${longDate.format(utcParts(iso).date)}`;

/**
 * Builds the GitHub-style yearly heatmap from the API payload
 * { total, weeks: [[[isoDate, count, level 0-4], …], …] }.
 * Real values only: levels come from GitHub, nothing is generated here.
 */
function renderContributionGraph(container, data) {
  const weeks = data.weeks.filter((w) => Array.isArray(w) && w.length);
  const columns = weeks.length;

  // matrix[row = weekday 0 (Sun) … 6][column = week]
  const matrix = Array.from({ length: 7 }, () => new Array(columns).fill(null));
  weeks.forEach((week, col) => {
    week.forEach(([date, count, level]) => {
      matrix[utcParts(date).weekday][col] = { date, count, level };
    });
  });

  // month header: label a column where the month changes; skip labels with less than 2 weeks of room
  const monthSpans = [];
  weeks.forEach((week, col) => {
    const month = utcParts(week[0][0]).month;
    const last = monthSpans[monthSpans.length - 1];
    if (!last || last.month !== month) monthSpans.push({ month, start: col, span: 1 });
    else last.span += 1;
  });

  const table = make('table', 'hm-table');
  table.setAttribute('role', 'grid');
  table.setAttribute('aria-label', `Contributions in the last year: ${data.total.toLocaleString('en-US')} in total. Use the arrow keys to move between days.`);

  const head = make('tr');
  head.append(make('td', 'hm-corner'));
  monthSpans.forEach((m) => {
    const th = make('th', 'hm-month', m.span >= 2 ? MONTH_SHORT[m.month] : '');
    th.scope = 'col';
    th.colSpan = m.span;
    head.append(th);
  });
  const thead = make('thead');
  thead.append(head);
  table.append(thead);

  const status = make('p', 'hm-status');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  status.textContent = 'Hover or focus a day to see its contributions.';

  const cells = [];
  const body = make('tbody');
  matrix.forEach((row, r) => {
    const tr = make('tr');
    const label = make('th', 'hm-day', WEEKDAY_ROW_LABELS[r]);
    label.scope = 'row';
    if (!WEEKDAY_ROW_LABELS[r]) label.setAttribute('aria-hidden', 'true');
    tr.append(label);
    cells[r] = [];
    row.forEach((day, c) => {
      if (!day) {
        const pad = make('td', 'hm-cell hm-pad');
        pad.setAttribute('aria-hidden', 'true');
        tr.append(pad);
        cells[r][c] = null;
        return;
      }
      const td = make('td', 'hm-cell');
      const text = contributionLabel(day.count, day.date);
      td.dataset.level = String(day.level);
      td.dataset.count = String(day.count);
      td.dataset.date = day.date;
      td.dataset.row = String(r);
      td.dataset.col = String(c);
      td.setAttribute('aria-label', text);
      td.title = text;
      td.tabIndex = -1;
      tr.append(td);
      cells[r][c] = td;
    });
    body.append(tr);
  });
  table.append(body);

  // roving tabindex: one tab stop for the whole grid, arrow keys inside it
  const all = cells.flat().filter(Boolean);
  const lastCell = all.reduce((latest, td) => (td.dataset.date > latest.dataset.date ? td : latest), all[0]);
  if (lastCell) lastCell.tabIndex = 0;
  const showStatus = (td) => {
    status.textContent = td.getAttribute('aria-label');
  };
  const focusCell = (td) => {
    all.forEach((c) => (c.tabIndex = -1));
    td.tabIndex = 0;
    td.focus();
  };
  table.addEventListener('focusin', (e) => e.target.matches('.hm-cell[data-date]') && showStatus(e.target));
  table.addEventListener('mouseover', (e) => e.target.matches('.hm-cell[data-date]') && showStatus(e.target));
  table.addEventListener('keydown', (e) => {
    const td = e.target.closest('.hm-cell[data-date]');
    if (!td) return;
    let r = Number(td.dataset.row);
    let c = Number(td.dataset.col);
    const step = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0] }[e.key];
    if (e.key === 'Home' || e.key === 'End') {
      const rowCells = cells[r].filter(Boolean);
      e.preventDefault();
      return focusCell(e.key === 'Home' ? rowCells[0] : rowCells[rowCells.length - 1]);
    }
    if (!step) return;
    e.preventDefault();
    for (;;) {
      r += step[0];
      c += step[1];
      if (r < 0 || r > 6 || c < 0 || c >= columns) return; // edge of the calendar
      if (cells[r][c]) return focusCell(cells[r][c]);
    }
  });

  const scroller = make('div', 'hm-scroll');
  scroller.tabIndex = 0;
  scroller.setAttribute('role', 'region');
  scroller.setAttribute('aria-label', 'Contribution calendar (scrollable)');
  scroller.append(table);

  const legend = make('div', 'hm-legend');
  legend.setAttribute('aria-hidden', 'true');
  legend.append('Less');
  for (let level = 0; level <= 4; level += 1) {
    const sw = make('span', 'hm-cell hm-swatch');
    sw.dataset.level = String(level);
    legend.append(sw);
  }
  legend.append('More');

  const foot = make('div', 'hm-foot');
  foot.append(status, legend);

  const title = $('#gh-graph-title');
  if (title) {
    title.replaceChildren();
    title.append(make('strong', null, data.total.toLocaleString('en-US')), ` contribution${data.total === 1 ? '' : 's'} in the last year`);
  }

  const parts = [scroller, foot];
  if (data.stale) parts.push(make('p', 'gh-note', `GitHub could not be reached just now; showing the last saved copy from ${timeAgo(data.generatedAt) || 'earlier'}.`));
  container.replaceChildren(...parts);
  container.removeAttribute('aria-busy');
  scroller.scrollLeft = scroller.scrollWidth; // most recent weeks visible first on narrow screens
}

const CONTRIBUTION_MESSAGES = {
  not_configured: 'The live contribution calendar is not enabled on this deployment yet.',
  rate_limited: 'GitHub’s request limit was reached, so the calendar is unavailable right now.',
  offline: 'You appear to be offline, so the calendar could not be loaded.',
  network: 'The calendar could not be loaded because the server could not be reached.',
};

function showContributionError(container, code) {
  const title = $('#gh-graph-title');
  if (title) title.textContent = 'Contribution activity';
  container.removeAttribute('aria-busy');
  const message = CONTRIBUTION_MESSAGES[code] || 'The contribution calendar is temporarily unavailable.';
  const p = make('p', 'gh-graph-msg', `${message} `);
  p.setAttribute('role', 'status');
  const link = make('a', 'gh-graph-link', 'View it on GitHub ↗');
  link.href = `https://github.com/${GITHUB_USERNAME}`;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  p.append(link);
  container.replaceChildren(p);
  if (code !== 'not_configured') {
    const retry = make('button', 'pg-btn ghost', 'Try again');
    retry.type = 'button';
    retry.style.marginTop = '12px';
    retry.addEventListener('click', loadContributionGraph);
    container.append(retry);
  }
}

async function loadContributionGraph() {
  const container = $('#gh-graph-body');
  if (!container) return;
  container.setAttribute('aria-busy', 'true');
  const skeleton = make('div', 'hm-skeleton');
  skeleton.setAttribute('aria-hidden', 'true');
  const loading = make('p', 'sr-only', 'Loading contribution calendar…');
  loading.setAttribute('role', 'status');
  container.replaceChildren(skeleton, loading);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(CONTRIBUTIONS_ENDPOINT, { headers: { Accept: 'application/json' }, signal: controller.signal });
    if (!response.ok) {
      let code = `http_${response.status}`;
      try {
        code = (await response.json()).error || code;
      } catch {
        /* non-JSON error page (for example 404 when running without the function) */
        if (response.status === 404) code = 'not_configured';
      }
      return showContributionError(container, code);
    }
    const data = await response.json();
    const valid =
      data &&
      Number.isFinite(data.total) &&
      Array.isArray(data.weeks) &&
      data.weeks.every((w) => Array.isArray(w) && w.every((d) => Array.isArray(d) && /^\d{4}-\d{2}-\d{2}$/.test(d[0]) && Number.isFinite(d[1]) && d[2] >= 0 && d[2] <= 4));
    if (!valid) return showContributionError(container, 'invalid');
    renderContributionGraph(container, data);
  } catch {
    showContributionError(container, navigator.onLine === false ? 'offline' : 'network');
  } finally {
    clearTimeout(timer);
  }
}

/* ---------- start: only when the section is near the viewport ---------- */

(function initGitHubSection() {
  const section = $('#github');
  if (!section) return;
  let started = false;

  function start() {
    if (started) return;
    started = true;
    loadGitHubData();
    loadContributionGraph();
  }

  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        io.disconnect();
        start();
      }
    }, { rootMargin: '400px 0px' });
    io.observe(section);
  } else {
    start();
  }

  // Keep the section current: when the tab becomes visible again and the cache has expired, refresh.
  document.addEventListener('visibilitychange', () => {
    if (!started || document.hidden) return;
    const cached = readGitHubCache();
    if (!cached || Date.now() - cached.savedAt >= GITHUB_CACHE_TTL_MS) loadGitHubData();
  });
  // Back online after an offline failure: try the calendar again.
  window.addEventListener('online', () => {
    if (started && $('#gh-graph-body .pg-btn')) loadContributionGraph();
  });
})();

/* ==========================================================================
   8. CONTACT FORM
   The form posts to the endpoint in its `action` attribute (Formspree).
   ========================================================================== */

(function initContactForm() {
  const form = $('#cform');
  if (!form) return;

  const status = $('#f-status');
  const submitButton = $('.f-btn', form);
  const submitMarkup = submitButton.innerHTML;

  const FIELDS = [
    {
      input: $('#f-name'),
      error: $('#f-name-err'),
      message: () => 'Please enter your name.',
    },
    {
      input: $('#f-email'),
      error: $('#f-email-err'),
      message: (input) =>
        input.validity.typeMismatch
          ? 'Please enter a valid email address, for example name@example.com.'
          : 'Please enter your email address.',
    },
    {
      input: $('#f-message'),
      error: $('#f-message-err'),
      message: () => 'Please write a message.',
    },
  ];

  function validateField(field) {
    const { input, error } = field;
    const empty = input.value.trim() === '';
    const invalid = empty || !input.validity.valid;

    if (invalid) {
      input.setAttribute('aria-invalid', 'true');
      input.setAttribute('aria-describedby', error.id);
      error.textContent = field.message(input);
      error.hidden = false;
    } else {
      input.removeAttribute('aria-invalid');
      input.removeAttribute('aria-describedby');
      error.textContent = '';
      error.hidden = true;
    }
    return !invalid;
  }

  function showStatus(message, { error = false, html = null } = {}) {
    status.className = error ? 'f-status is-error' : 'f-status';
    status.replaceChildren();
    if (html) status.append(...html);
    else status.textContent = message;
    status.hidden = false;
  }

  function clearStatus() {
    status.hidden = true;
    status.textContent = '';
  }

  FIELDS.forEach((field) => {
    // Validate once the person leaves a field, and clear the error as soon as it is fixed.
    field.input.addEventListener('blur', () => {
      if (field.input.value !== '' || field.input.hasAttribute('aria-invalid')) validateField(field);
    });
    field.input.addEventListener('input', () => {
      if (field.input.hasAttribute('aria-invalid')) validateField(field);
    });
  });

  function setSending(sending) {
    submitButton.disabled = sending;
    submitButton.setAttribute('aria-busy', String(sending));
    if (sending) {
      submitButton.innerHTML =
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" style="animation:spin .7s linear infinite"><path d="M21 12a9 9 0 1 1-6.22-8.56"/></svg> Sending...';
    } else {
      submitButton.innerHTML = submitMarkup;
    }
  }

  function showSuccess() {
    const box = document.createElement('div');
    box.className = 'f-ok';
    box.tabIndex = -1;
    box.setAttribute('role', 'status');

    const icon = document.createElement('div');
    icon.className = 'f-ok-ico';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '✅';

    const text = document.createElement('p');
    text.append('Message sent!', document.createElement('br'), 'Thank you for reaching out. I’ll get back to you soon.');

    box.append(icon, text);
    form.replaceChildren(box);
    box.focus();
  }

  function showSendFailure() {
    const email = document.createElement('a');
    email.href = 'mailto:moustafa.mahmoudx7@gmail.com';
    email.textContent = 'email';
    const whatsapp = document.createElement('a');
    whatsapp.href = 'https://wa.me/201127434078';
    whatsapp.target = '_blank';
    whatsapp.rel = 'noopener noreferrer';
    whatsapp.textContent = 'WhatsApp';

    showStatus('', {
      error: true,
      html: [
        document.createTextNode('Your message could not be sent. Your text is still here, so you can try again, or reach me by '),
        email,
        document.createTextNode(' or '),
        whatsapp,
        document.createTextNode('.'),
      ],
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearStatus();

    const results = FIELDS.map(validateField);
    const firstInvalid = FIELDS.find((_, i) => !results[i]);
    if (firstInvalid) {
      showStatus('Please correct the highlighted fields and try again.', { error: true });
      firstInvalid.input.focus();
      return;
    }

    // Honeypot: real visitors never see or fill this field.
    if ($('[name="_gotcha"]', form).value) {
      showSuccess();
      return;
    }

    setSending(true);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Form endpoint responded with ${response.status}`);
      showSuccess();
    } catch (error) {
      console.error('Contact form submission failed:', error);
      setSending(false);
      showSendFailure();
    } finally {
      clearTimeout(timer);
    }
  });
})();


/* ==========================================================================
   8b. CERTIFICATES — filter + viewer (native <dialog>: focus trap, Esc and
   focus restoration come from the browser; arrows, swipe and states added here)
   ========================================================================== */

(function initCertificates() {
  const grid = $('#cert-grid');
  const dialog = $('#cert-viewer');
  if (!grid || !dialog) return;

  const status = $('#cert-status');
  const filters = $$('.cert-filter');
  const items = $$('.cert-item', grid);
  const img = $('#cv-img');
  const stateEl = $('#cv-state');
  const errorEl = $('#cv-error');
  const openLink = $('#cv-open');
  const titleEl = $('#cv-title');
  const subEl = $('#cv-sub');
  const countEl = $('#cv-count');
  const prevBtn = $('#cv-prev');
  const nextBtn = $('#cv-next');
  let current = 0;
  let lastTile = null;
  let loadToken = 0;

  const visibleTiles = () => items.filter((li) => !li.hidden).map((li) => $('.cert-tile', li));

  /* filtering */
  function applyFilter(id) {
    filters.forEach((btn) => btn.setAttribute('aria-pressed', String(btn.dataset.filter === id)));
    items.forEach((li) => {
      li.hidden = !(id === 'all' || li.dataset.category === id);
    });
    const n = visibleTiles().length;
    if (status) status.textContent = `Showing ${n} ${n === 1 ? 'certificate' : 'certificates'}.`;
  }
  filters.forEach((btn) => btn.addEventListener('click', () => applyFilter(btn.dataset.filter)));

  /* viewer */
  function show(index) {
    const tiles = visibleTiles();
    if (!tiles.length) return;
    current = (index + tiles.length) % tiles.length;
    const t = tiles[current].dataset;
    const token = ++loadToken;

    countEl.textContent = `${current + 1} / ${tiles.length}`;
    titleEl.textContent = t.title;
    subEl.textContent = [t.type, t.issuer, t.date].filter(Boolean).join(' · ');
    prevBtn.disabled = nextBtn.disabled = tiles.length < 2;

    errorEl.hidden = true;
    openLink.href = t.full;
    img.alt = t.alt;

    // Instant feedback: the card's thumbnail is already in the cache, so the viewer paints at once
    // and the full-size image replaces it as soon as it has loaded and decoded.
    const preview = $('img', tiles[current]);
    if (preview && preview.currentSrc) {
      img.src = preview.currentSrc;
      stateEl.hidden = true;
      img.classList.add('is-ready');
    } else {
      img.classList.remove('is-ready');
      stateEl.hidden = false;
      stateEl.textContent = 'Loading certificate…';
    }

    const full = new Image();
    full.decoding = 'async';
    full.onload = () => {
      if (token !== loadToken) return;
      const swap = () => {
        if (token !== loadToken) return;
        img.src = t.full;
        stateEl.hidden = true;
        img.classList.add('is-ready');
      };
      if (full.decode) full.decode().then(swap, swap);
      else swap();
    };
    full.onerror = () => {
      if (token !== loadToken) return;
      stateEl.hidden = true;
      errorEl.hidden = false;
    };
    full.src = t.full;

    // warm the cache for the neighbours when the browser is idle (not during the open interaction)
    const warm = () =>
      [tiles[(current + 1) % tiles.length], tiles[(current - 1 + tiles.length) % tiles.length]].forEach((n) => {
        new Image().src = n.dataset.full;
      });
    if ('requestIdleCallback' in window) requestIdleCallback(warm, { timeout: 1500 });
    else setTimeout(warm, 300);
  }

  grid.addEventListener('click', (e) => {
    const tile = e.target.closest('.cert-tile');
    if (!tile) return;
    if (typeof dialog.showModal !== 'function') {
      window.open(tile.dataset.full, '_blank', 'noopener');
      return;
    }
    lastTile = tile;
    show(visibleTiles().indexOf(tile));
    dialog.showModal();
    $('#cv-close').focus();
  });

  prevBtn.addEventListener('click', () => show(current - 1));
  nextBtn.addEventListener('click', () => show(current + 1));
  $('#cv-close').addEventListener('click', () => dialog.close());

  // explicit focus trap: Tab / Shift+Tab wrap around the viewer's own controls
  dialog.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    const focusable = $$('button:not([disabled]), a[href]', dialog).filter((n) => !n.hidden && n.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  dialog.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      show(current - 1);
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      show(current + 1);
    }
  });

  // Keep the page behind from scrolling while the viewer is open — without toggling overflow on <html>
  // (that forces a full-page relayout, which made opening the viewer slow on phones).
  const stopBackdropScroll = (e) => {
    if (e.target === dialog) e.preventDefault();
  };
  dialog.addEventListener('wheel', stopBackdropScroll, { passive: false });
  dialog.addEventListener('touchmove', stopBackdropScroll, { passive: false });

  // click on the backdrop (outside the dialog box) closes it
  dialog.addEventListener('click', (e) => {
    const r = dialog.getBoundingClientRect();
    const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
    if (!inside) dialog.close();
  });

  dialog.addEventListener('close', () => {
    loadToken += 1;
    img.removeAttribute('src');
    if (lastTile) lastTile.focus();
  });

  // swipe left/right on touch screens
  const stage = $('#cv-stage');
  let startX = 0;
  let startY = 0;
  stage.addEventListener('pointerdown', (e) => {
    if (e.pointerType !== 'touch') return;
    startX = e.clientX;
    startY = e.clientY;
  });
  stage.addEventListener('pointerup', (e) => {
    if (e.pointerType !== 'touch') return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 2) show(current + (dx < 0 ? 1 : -1));
  });
})();

/* ==========================================================================
   8c. DEV PLAYGROUND — nothing is downloaded until the section is near the
   viewport; each game's module loads the first time its tab is shown.
   ========================================================================== */

(function initPlayground() {
  const app = $('#playground-app');
  if (!app) return;

  const tabs = $$('.pg-tab', app);
  const panels = { bug: $('#panel-bug'), sushi: $('#panel-sushi') };
  const loaders = {
    bug: () => import('./games/bug-hunter.js'),
    sushi: () => import('./games/sushi-bounce.js'),
  };
  const controllers = {};
  const loading = {};
  let selected = 'bug';
  let armed = false;

  async function ensure(game) {
    if (controllers[game] || loading[game]) return;
    const mount = $(`[data-mount="${game}"]`, app);
    loading[game] = true;
    try {
      const module = await loaders[game]();
      controllers[game] = module.mount(mount);
    } catch (error) {
      console.error(`Could not load ${game}:`, error);
      mount.replaceChildren();
      const p = document.createElement('p');
      p.className = 'pg-loading';
      p.textContent = 'This game could not be loaded. ';
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.className = 'pg-btn ghost';
      retry.textContent = 'Try again';
      retry.addEventListener('click', () => {
        mount.replaceChildren(Object.assign(document.createElement('p'), { className: 'pg-loading', textContent: 'Loading…' }));
        ensure(game);
      });
      p.append(retry);
      mount.append(p);
    } finally {
      loading[game] = false;
    }
  }

  function select(game, { focus = false } = {}) {
    selected = game;
    tabs.forEach((tab) => {
      const active = tab.dataset.game === game;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      panels[tab.dataset.game].hidden = !active;
      if (active && focus) tab.focus();
    });
    Object.entries(controllers).forEach(([name, c]) => name !== game && c.pause && c.pause());
    if (armed) ensure(game);
  }

  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => select(tab.dataset.game));
    tab.addEventListener('keydown', (e) => {
      const move = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (move) {
        e.preventDefault();
        select(tabs[(i + move + tabs.length) % tabs.length].dataset.game, { focus: true });
      } else if (e.key === 'Home' || e.key === 'End') {
        e.preventDefault();
        select(tabs[e.key === 'Home' ? 0 : tabs.length - 1].dataset.game, { focus: true });
      }
    });
  });

  function arm() {
    armed = true;
    ensure(selected);
  }
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        io.disconnect();
        arm();
      }
    }, { rootMargin: '300px 0px' });
    io.observe(app);
  } else {
    arm();
  }
})();

/* ==========================================================================
   9. PAGE LOADER — never waits on window.load or an artificial delay
   ========================================================================== */

(function hideLoader() {
  const loader = $('#loader');
  if (!loader) return;
  const hide = () =>
    requestAnimationFrame(() => {
      loader.classList.add('hidden');
      setTimeout(() => loader.remove(), 350);
    });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hide, { once: true });
  else hide();
})();

/* ==========================================================================
   10. ACTIVE NAV LINK, SCROLL-LINKED UI, FOOTER YEAR
   ========================================================================== */

(function initScrollUi() {
  const nav = $('#nav');
  const toTop = $('#stt');

  // One passive, frame-throttled scroll listener for everything scroll-linked.
  const update = rafThrottle(() => {
    const y = window.scrollY;
    if (nav) nav.classList.toggle('solid', y > 50);
    if (toTop) toTop.classList.toggle('show', y > 400);
  });
  window.addEventListener('scroll', update, { passive: true });
  update();

  if (toTop) {
    toTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: reducedMotion.matches ? 'auto' : 'smooth' });
    });
  }
})();

(function highlightActiveNavLink() {
  if (!('IntersectionObserver' in window)) return;
  const sectionIds = ['hero', 'about', 'education', 'skills', 'projects', 'github', 'experience', 'certificates', 'contact'];
  const navLinks = $$('.n-links a');

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((link) => {
          const active = link.getAttribute('href') === `#${entry.target.id}`;
          link.classList.toggle('active', active);
          if (active) link.setAttribute('aria-current', 'location');
          else link.removeAttribute('aria-current');
        });
      });
    },
    // A thin band around the middle of the viewport: works for sections taller than the screen too.
    { threshold: 0, rootMargin: '-45% 0px -54% 0px' }
  );

  sectionIds.forEach((id) => {
    const section = document.getElementById(id);
    if (section) observer.observe(section);
  });
})();

(function setFooterYear() {
  const year = $('#yr');
  if (year) year.textContent = String(new Date().getFullYear());
})();
