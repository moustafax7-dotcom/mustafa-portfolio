/**
 * Sushi Bounce — keep the sushi alive by bouncing it off your paddle.
 * Independent Canvas implementation of the mechanics verified against the reference
 * game's published source (see docs/REPORT.md → "Sushi Bounce: reference vs. mine").
 * Loaded on demand by main.js. mount(root) → { pause, resume, start, destroy, getState, … }.
 *
 * Units: CSS pixels. The reference moves things "per animation frame" at 60 fps, so this
 * version runs the physics in fixed 1/60 s steps and converts real elapsed time into steps.
 * The game therefore plays identically on 60 Hz, 120 Hz and 144 Hz screens (the reference
 * runs twice as fast on a 120 Hz display).
 */

// ── verified from the reference ────────────────────────────────────────────────
const LIVES_AT_START = 3;
const SUSHI = 42; // sushi box, px
const PADDLE_W = 110;
const PADDLE_H = 15;
const PADDLE_BOTTOM = 22; // gap between paddle and board bottom
const SMALL_PADDLE = { w: 95, h: 14, bottom: 20 }; // used when the viewport is ≤ 700 px wide
const START_Y = 80; // sushi top edge when (re)spawned
const BASE_SPEED = 3; // px per step, both axes
const SPEED_PER_POINT = 0.08;
const SPEED_BONUS_MAX = 3; // speed = 3 + min(score × 0.08, 3)
const STEP = 1000 / 60; // ms per physics step
// ── input (intentionally better than the reference, see report) ───────────────
const KEY_NUDGE = 35; // px on the first press of ← / →, like the reference
const KEY_SPEED = 12; // px per step while the key stays held (720 px/s)
const MAX_STEPS_PER_FRAME = 5; // after a long stall we do not "catch up" for seconds

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};
const NS = 'http://www.w3.org/2000/svg';

function lifeIcon() {
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 22 14');
  svg.setAttribute('class', 'sb-life');
  svg.setAttribute('aria-hidden', 'true');
  svg.innerHTML =
    '<rect x="2" y="6" width="18" height="7" rx="3.5" fill="#f4f1ea"/><rect x="1" y="1.5" width="20" height="6" rx="3" fill="#ff7a59"/><rect x="9" y="1" width="4" height="12" rx="1" fill="#1d3b2f"/>';
  return svg;
}

export function mount(root) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const small = window.matchMedia('(max-width: 700px)');
  const listeners = [];
  const on = (target, type, fn, opts) => {
    target.addEventListener(type, fn, opts);
    listeners.push(() => target.removeEventListener(type, fn, opts));
  };

  /* ---------- DOM ---------- */
  const wrap = el('div', 'sb');
  const hud = el('div', 'sb-hud');
  const scoreWrap = el('span', 'sb-stat');
  scoreWrap.append(el('span', 'sb-label', 'Score'));
  const scoreEl = el('b', null, '0');
  scoreEl.dataset.role = 'score';
  scoreWrap.append(scoreEl);
  const livesWrap = el('span', 'sb-lives sb-stat');
  livesWrap.dataset.role = 'lives';
  livesWrap.setAttribute('role', 'img');
  const livesNum = el('b', null, String(LIVES_AT_START));
  const pauseBtn = el('button', 'pg-btn ghost', 'Pause');
  pauseBtn.type = 'button';
  pauseBtn.dataset.role = 'pause';
  pauseBtn.style.minHeight = '36px';
  pauseBtn.style.padding = '6px 14px';
  hud.append(scoreWrap, livesWrap, pauseBtn);

  const stage = el('div', 'sb-stage');
  stage.tabIndex = 0;
  stage.setAttribute('role', 'group');
  stage.setAttribute('aria-label', 'Sushi Bounce game area. Move the paddle with the left and right arrow keys, A and D, the mouse or by dragging.');
  const canvas = el('canvas', 'sb-canvas');
  canvas.setAttribute('aria-hidden', 'true');
  const overlay = el('div', 'sb-overlay');
  overlay.dataset.role = 'overlay';
  stage.append(canvas, overlay);

  const controls = el('div', 'sb-controls');
  const keyHint = el('span', 'sb-key', '← Move → or drag on mobile · P or Esc to pause');
  const pad = el('div', 'sb-pad');
  const leftBtn = el('button', 'pg-btn ghost', '◀');
  const rightBtn = el('button', 'pg-btn ghost', '▶');
  leftBtn.type = rightBtn.type = 'button';
  leftBtn.setAttribute('aria-label', 'Move paddle left (hold)');
  rightBtn.setAttribute('aria-label', 'Move paddle right (hold)');
  pad.append(leftBtn, rightBtn);
  controls.append(keyHint, pad);

  const live = el('p', 'sr-only');
  live.setAttribute('role', 'status');
  live.setAttribute('aria-live', 'polite');
  wrap.append(hud, stage, controls, live);
  root.replaceChildren(wrap);

  const ctx = canvas.getContext('2d');

  /* ---------- state ---------- */
  const game = {
    mode: 'ready', // ready | playing | paused | over
    score: 0,
    lives: LIVES_AT_START,
    w: 700, // board size in CSS px (set by resize())
    h: 430,
    paddleX: 0, // paddle left edge
    paddle: { w: PADDLE_W, h: PADDLE_H, bottom: PADDLE_BOTTOM },
    // sushi box top-left corner and velocity, in px per physics step
    ball: { x: 0, y: START_Y, vx: BASE_SPEED, vy: BASE_SPEED, spin: 0 },
    flash: 0,
    pausedBy: null,
    resumeTo: 'playing',
  };
  const keys = { left: false, right: false };
  let rafId = 0;
  let lastT = 0;
  let acc = 0;
  let dpr = 1;
  let bgLayer = null; // static background, drawn once per resize
  let visible = true;

  const paddleTop = () => game.h - game.paddle.bottom - game.paddle.h;
  const speedFor = (score) => BASE_SPEED + Math.min(score * SPEED_PER_POINT, SPEED_BONUS_MAX);
  const clampPaddle = () => {
    game.paddleX = Math.max(0, Math.min(game.paddleX, game.w - game.paddle.w));
  };
  const announce = (text) => {
    live.textContent = text;
  };

  /* ---------- HUD ---------- */
  function renderHud() {
    scoreEl.textContent = String(game.score);
    livesNum.textContent = String(Math.max(0, game.lives));
    livesWrap.replaceChildren(el('span', 'sb-label', 'Lives'), livesNum);
    for (let i = 0; i < LIVES_AT_START; i += 1) {
      const icon = lifeIcon();
      if (i >= game.lives) icon.style.opacity = '.18';
      livesWrap.append(icon);
    }
    livesWrap.setAttribute('aria-label', `${game.lives} ${game.lives === 1 ? 'life' : 'lives'} left`);
    pauseBtn.disabled = game.mode === 'ready' || game.mode === 'over';
    pauseBtn.textContent = game.mode === 'paused' ? 'Resume' : 'Pause';
  }

  function showOverlay(kind) {
    overlay.replaceChildren();
    overlay.hidden = kind === null;
    if (kind === null) return;
    const btn = el('button', 'pg-btn');
    btn.type = 'button';
    btn.dataset.role = 'primary';
    if (kind === 'ready') {
      overlay.append(el('h3', null, 'Sushi Bounce'), el('p', null, 'Keep the sushi alive!'));
      overlay.append(el('p', 'sb-sub', 'Bounce it off your paddle to score. Miss it and you lose a life. You have 3.'));
      overlay.append(el('p', 'sb-sub', '← Move → or drag on mobile'));
      btn.textContent = 'Start Game';
      btn.addEventListener('click', start);
    } else if (kind === 'paused') {
      overlay.append(el('h3', null, 'Paused'), el('p', null, game.pausedBy === 'auto' ? 'The game paused because it left the screen or the tab was hidden.' : 'Take your time.'));
      btn.textContent = 'Resume';
      btn.addEventListener('click', resume);
    } else {
      overlay.append(el('span', 'sb-over-ico', '🍣'), el('h3', null, 'Oops!'), el('p', null, 'Your sushi escaped.'), el('p', 'sb-sub', `Final score: ${game.score}`));
      btn.textContent = 'Play Again';
      btn.addEventListener('click', start);
    }
    overlay.append(btn);
  }

  /* ---------- sizing ---------- */
  function resize() {
    const rect = stage.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    game.w = rect.width;
    game.h = rect.height;
    game.paddle = small.matches ? { ...SMALL_PADDLE } : { w: PADDLE_W, h: PADDLE_H, bottom: PADDLE_BOTTOM };
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    clampPaddle();
    game.ball.x = Math.max(0, Math.min(game.ball.x, game.w - SUSHI));
    buildStatic();
    draw();
  }

  /* ---------- game flow ---------- */
  function spawn() {
    game.ball.x = game.w / 2 - SUSHI / 2;
    game.ball.y = START_Y;
    game.ball.vx = Math.random() > 0.5 ? BASE_SPEED : -BASE_SPEED;
    game.ball.vy = BASE_SPEED;
    game.ball.spin = 0;
  }

  function start() {
    game.score = 0;
    game.lives = LIVES_AT_START;
    game.flash = 0;
    game.pausedBy = null;
    game.paddleX = game.w / 2 - game.paddle.w / 2;
    spawn();
    acc = 0;
    setMode('playing');
    announce('Game started. 3 lives.');
    stage.focus({ preventScroll: true });
  }

  function setMode(mode) {
    game.mode = mode;
    showOverlay(mode === 'ready' ? 'ready' : mode === 'paused' ? 'paused' : mode === 'over' ? 'over' : null);
    renderHud();
    if (mode === 'playing') startLoop();
    else stopLoop();
    draw();
    if (mode === 'over' || mode === 'paused') overlay.querySelector('[data-role="primary"]')?.focus({ preventScroll: true });
  }

  function pause(reason = 'user') {
    if (game.mode !== 'playing') return;
    game.pausedBy = reason;
    keys.left = keys.right = false;
    setMode('paused');
    announce('Paused.');
  }

  function resume() {
    if (game.mode !== 'paused') return;
    game.pausedBy = null;
    acc = 0;
    setMode('playing');
    stage.focus({ preventScroll: true });
    announce('Resumed.');
  }

  function loseLife() {
    game.lives -= 1;
    game.flash = reduceMotion.matches ? 0 : 0.35;
    if (game.lives <= 0) {
      announce(`Game over. Final score ${game.score}.`);
      setMode('over');
    } else {
      announce(`You lost a life. ${game.lives} left.`);
      spawn(); // like the reference: respawn right away, score and paddle stay
      renderHud();
    }
  }

  /* ---------- simulation: ONE reference "frame" = one step ---------- */
  function step() {
    if (game.mode !== 'playing') return;
    const b = game.ball;

    const dir = (keys.right ? 1 : 0) - (keys.left ? 1 : 0);
    if (dir) {
      game.paddleX += dir * KEY_SPEED;
      clampPaddle();
    }
    if (game.flash > 0) game.flash = Math.max(0, game.flash - STEP / 1000);

    b.x += b.vx;
    b.y += b.vy;
    b.spin += (b.vx >= 0 ? 1 : -1) * 0.05;

    // walls and ceiling
    if (b.x <= 0) {
      b.x = 0;
      b.vx *= -1;
    }
    if (b.x + SUSHI >= game.w) {
      b.x = game.w - SUSHI;
      b.vx *= -1;
    }
    if (b.y <= 0) {
      b.y = 0;
      b.vy *= -1;
    }

    // paddle: moving down, bottom reached the paddle, and the sushi's horizontal centre is over it
    const top = paddleTop();
    const bottom = b.y + SUSHI;
    const centerX = b.x + SUSHI / 2;
    if (b.vy > 0 && bottom >= top && b.y <= top + game.paddle.h && centerX >= game.paddleX && centerX <= game.paddleX + game.paddle.w) {
      b.y = top - SUSHI;
      b.vy *= -1;
      game.score += 1;
      scoreEl.textContent = String(game.score);
      const speed = speedFor(game.score);
      b.vx = b.vx > 0 ? speed : -speed;
      b.vy = -Math.abs(b.vy);
      if (Math.abs(b.vy) < speed) b.vy = -speed;
      if (game.score % 5 === 0) announce(`Score ${game.score}`);
    }

    // lost: the whole sushi has fallen below the board (reference: top edge below the bottom)
    if (b.y > game.h) loseLife();
  }

  /* ---------- rendering (original artwork) ---------- */
  function roundRect(c, x, y, w, h, r) {
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }

  /** Background never changes between frames: render it once per size. */
  function buildStatic() {
    const layer = document.createElement('canvas');
    layer.width = canvas.width;
    layer.height = canvas.height;
    const c = layer.getContext('2d');
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    const bg = c.createLinearGradient(0, 0, 0, game.h);
    bg.addColorStop(0, '#0c0e16');
    bg.addColorStop(1, '#11141f');
    c.fillStyle = bg;
    c.fillRect(0, 0, game.w, game.h);
    // faint dot grid (the reference board has one too), in the portfolio's blue
    c.fillStyle = 'rgba(79,142,247,.10)';
    for (let x = 6; x < game.w; x += 30) for (let y = 6; y < game.h; y += 30) c.fillRect(x, y, 1.5, 1.5);
    bgLayer = layer;
  }

  function drawSushi(x, y, spin) {
    // x, y = top-left of the 42 px box
    const r = SUSHI / 2;
    ctx.save();
    ctx.translate(x + r, y + r);
    ctx.rotate(reduceMotion.matches ? 0 : Math.sin(spin) * 0.35);
    const w = SUSHI * 0.95;
    const h = SUSHI * 0.6;
    ctx.fillStyle = '#f4f1ea'; // rice
    roundRect(ctx, -w / 2, -h * 0.05, w, h * 0.62, h * 0.3);
    ctx.fill();
    ctx.fillStyle = '#ff7a59'; // topping
    roundRect(ctx, -w * 0.53, -h * 0.55, w * 1.06, h * 0.62, h * 0.3);
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,.55)';
    ctx.lineWidth = 1.2;
    for (let i = -1; i <= 1; i += 1) {
      ctx.beginPath();
      ctx.moveTo(i * w * 0.24 - w * 0.07, -h * 0.5);
      ctx.lineTo(i * w * 0.24 + w * 0.07, 0);
      ctx.stroke();
    }
    ctx.fillStyle = '#1d3b2f'; // nori band
    roundRect(ctx, -w * 0.09, -h * 0.58, w * 0.18, h * 1.2, 2);
    ctx.fill();
    ctx.restore();
  }

  function draw() {
    if (!bgLayer) return;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(bgLayer, 0, 0);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // paddle (serving board)
    const py = paddleTop();
    ctx.fillStyle = '#c4894f';
    roundRect(ctx, game.paddleX, py, game.paddle.w, game.paddle.h, game.paddle.h / 2);
    ctx.fill();
    ctx.fillStyle = '#4f8ef7';
    roundRect(ctx, game.paddleX + game.paddle.w * 0.12, py + game.paddle.h * 0.3, game.paddle.w * 0.76, game.paddle.h * 0.2, 2);
    ctx.fill();

    drawSushi(game.ball.x, game.ball.y, game.ball.spin);

    if (game.flash > 0) {
      ctx.fillStyle = `rgba(248,113,113,${game.flash * 0.9})`;
      ctx.fillRect(0, 0, game.w, game.h);
    }
  }

  /* ---------- loop: one rAF, only while playing; fixed 60 Hz physics ---------- */
  function frame(t) {
    acc += Math.min(t - lastT, STEP * MAX_STEPS_PER_FRAME);
    lastT = t;
    let steps = 0;
    while (acc >= STEP && steps < MAX_STEPS_PER_FRAME) {
      step();
      acc -= STEP;
      steps += 1;
      if (game.mode !== 'playing') break;
    }
    draw();
    rafId = game.mode === 'playing' ? requestAnimationFrame(frame) : 0;
  }
  function startLoop() {
    if (rafId) return;
    lastT = performance.now();
    rafId = requestAnimationFrame(frame);
  }
  function stopLoop() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = 0;
  }

  /* ---------- input ---------- */
  const KEYMAP = { ArrowLeft: 'left', a: 'left', A: 'left', ArrowRight: 'right', d: 'right', D: 'right' };
  on(window, 'keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const active = game.mode === 'playing';
    if ((e.key === 'Escape' || e.key === 'p' || e.key === 'P') && (active || game.mode === 'paused') && visible) {
      if (e.key === 'Escape' && !root.contains(document.activeElement) && game.mode !== 'paused') return;
      e.preventDefault();
      if (active) pause('user');
      else resume();
      return;
    }
    const dir = KEYMAP[e.key];
    // Only while the game is running AND on screen: the page scrolls normally otherwise
    // (the reference blocks arrow-key scrolling for the whole page, always).
    if (dir && active && visible) {
      e.preventDefault();
      if (!e.repeat) {
        game.paddleX += (dir === 'left' ? -1 : 1) * KEY_NUDGE; // first press moves 35 px like the reference
        clampPaddle();
      }
      keys[dir] = true;
    }
  });
  on(window, 'keyup', (e) => {
    const dir = KEYMAP[e.key];
    if (dir) keys[dir] = false;
  });
  on(window, 'blur', () => {
    keys.left = keys.right = false;
  });

  function movePaddleTo(clientX) {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width) return;
    game.paddleX = clientX - rect.left - game.paddle.w / 2; // centred on the pointer
    clampPaddle();
    if (game.mode !== 'playing') draw();
  }
  on(canvas, 'pointerdown', (e) => {
    if (game.mode !== 'playing') return;
    try {
      canvas.setPointerCapture(e.pointerId);
    } catch {
      /* synthetic or released pointer */
    }
    movePaddleTo(e.clientX);
  });
  on(canvas, 'pointermove', (e) => {
    if (game.mode !== 'playing') return;
    let captured = false;
    try {
      captured = canvas.hasPointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    if (e.pointerType === 'mouse' || captured) movePaddleTo(e.clientX);
  });

  [[leftBtn, 'left'], [rightBtn, 'right']].forEach(([btn, dir]) => {
    on(btn, 'pointerdown', (e) => {
      e.preventDefault();
      keys[dir] = true;
    });
    ['pointerup', 'pointerleave', 'pointercancel'].forEach((type) => on(btn, type, () => (keys[dir] = false)));
    on(btn, 'keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') keys[dir] = true;
    });
    on(btn, 'keyup', (e) => {
      if (e.key === ' ' || e.key === 'Enter') keys[dir] = false;
    });
  });

  on(pauseBtn, 'click', () => (game.mode === 'paused' ? resume() : pause('user')));

  /* ---------- lifecycle: auto-pause, resize ---------- */
  on(document, 'visibilitychange', () => {
    if (document.hidden) pause('auto');
  });
  const ro = new ResizeObserver(resize);
  ro.observe(stage);
  on(small, 'change', resize);
  const io = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (!visible) pause('auto');
  }, { threshold: 0.25 });
  io.observe(stage);

  renderHud();
  showOverlay('ready');
  resize();
  game.paddleX = game.w / 2 - game.paddle.w / 2;
  draw();

  return {
    pause: () => pause('auto'),
    resume,
    start,
    destroy() {
      stopLoop();
      listeners.forEach((off) => off());
      ro.disconnect();
      io.disconnect();
      root.replaceChildren();
    },
    // read-only snapshot + deterministic hooks used by tests/features.py (not used by the page)
    getState: () => ({
      mode: game.mode,
      score: game.score,
      lives: game.lives,
      paddleX: game.paddleX,
      paddle: { ...game.paddle },
      board: { w: game.w, h: game.h },
      ball: { ...game.ball },
      speed: Math.abs(game.ball.vx),
      raf: Boolean(rafId),
      canvas: [canvas.width, canvas.height],
    }),
    _step: step, // one 1/60 s physics step (= one frame of the reference)
    _setBall: (x, y, vx, vy) => Object.assign(game.ball, { x, y, vx, vy }),
    _setPaddle: (x) => {
      game.paddleX = x;
      clampPaddle();
    },
    _setScore: (n) => {
      game.score = n;
    },
    _forceMode: (m) => {
      if (m === 'playing') game.mode = 'playing';
    },
  };
}
