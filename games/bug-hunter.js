/**
 * Bug Hunter — spot the buggy line in a short JavaScript snippet.
 * Loaded on demand by main.js. mount(root) → { destroy, pause }.
 * Every snippet has exactly one buggy line (1-based `bug`) and a verified explanation.
 */

const QUESTIONS = [
  {
    level: 'easy',
    prompt: 'This should print the sum of the array (6). Which line is wrong?',
    code: ['const nums = [1, 2, 3];', 'let total = 0;', 'for (let i = 0; i <= nums.length; i++) {', '  total += nums[i];', '}', 'console.log(total); // expected 6'],
    bug: 3,
    explain: '`i <= nums.length` makes the loop run one time too many. On the last pass `nums[3]` is `undefined`, so `total` becomes `NaN`. Use `i < nums.length`.',
  },
  {
    level: 'easy',
    prompt: 'The message should print only when age is exactly 18. Which line is wrong?',
    code: ['let age = 18;', 'if (age = 18) {', '  console.log("Exactly 18");', '}'],
    bug: 2,
    explain: 'A single `=` assigns 18 to `age` instead of comparing. The condition then always passes, for any age. Use `age === 18`.',
  },
  {
    level: 'easy',
    prompt: 'The total should be 13 (10 + 3). Which line is wrong?',
    code: ['const price = "10";', 'const quantity = 3;', 'const total = price + quantity;', 'console.log(total); // expected 13'],
    bug: 3,
    explain: 'When one operand is a string, `+` joins text, so the result is `"103"`. Convert first: `Number(price) + quantity`.',
  },
  {
    level: 'easy',
    prompt: 'double(4) should return 8. Which line is wrong?',
    code: ['function double(n) {', '  n * 2;', '}', 'console.log(double(4)); // expected 8'],
    bug: 2,
    explain: 'The result of `n * 2` is calculated and then thrown away. Without `return`, the function returns `undefined`. Write `return n * 2;`.',
  },
  {
    level: 'easy',
    prompt: 'This should print the last item, "c". Which line is wrong?',
    code: ['const items = ["a", "b", "c"];', 'const last = items[items.length];', 'console.log(last); // expected "c"'],
    bug: 2,
    explain: 'Array indexes start at 0, so the last index is `items.length - 1`. `items[3]` does not exist and gives `undefined`.',
  },
  {
    level: 'easy',
    prompt: 'This should print "Sara". Which line is wrong?',
    code: ['const user = { name: "Sara", age: 21 };', 'console.log(user.nmae); // expected "Sara"'],
    bug: 2,
    explain: 'The property name is misspelled. `user.nmae` does not exist, so JavaScript returns `undefined`. Use `user.name`.',
  },
  {
    level: 'easy',
    prompt: 'isEven(4) should return true. Which line is wrong?',
    code: ['function isEven(n) {', '  return n % 2 === 1;', '}', 'console.log(isEven(4)); // expected true'],
    bug: 2,
    explain: 'An even number leaves a remainder of 0 when divided by 2, not 1. The check should be `n % 2 === 0`.',
  },
  {
    level: 'medium',
    prompt: 'This should print the highest score, 9. Which line is wrong?',
    code: ['const scores = [4, 9, 2];', 'const best = Math.max(scores);', 'console.log(best); // expected 9'],
    bug: 2,
    explain: '`Math.max` expects separate numbers, not an array. Passing the array gives `NaN`. Spread it instead: `Math.max(...scores)`.',
  },
  {
    level: 'medium',
    prompt: 'This should print [1, 9, 10]. Which line is wrong?',
    code: ['const nums = [10, 9, 1];', 'nums.sort();', 'console.log(nums); // expected [1, 9, 10]'],
    bug: 2,
    explain: 'Without a compare function, `sort()` orders values as strings, which gives `[1, 10, 9]`. Pass a comparer: `nums.sort((a, b) => a - b)`.',
  },
  {
    level: 'medium',
    prompt: 'This should log 0, 1, 2. It logs 3, 3, 3. Which line causes it?',
    code: ['for (var i = 0; i < 3; i++) {', '  setTimeout(() => console.log(i), 0);', '}', '// expected output: 0, 1, 2'],
    bug: 1,
    explain: '`var` is function-scoped, so every callback shares one `i`, which is already 3 when they run. Declare it with `let` so each loop pass gets its own `i`.',
  },
  {
    level: 'medium',
    prompt: 'This should print true. It prints false. Which line is wrong?',
    code: ['const sum = 0.1 + 0.2;', 'console.log(sum === 0.3); // expected true'],
    bug: 2,
    explain: 'Decimal fractions are stored as binary floating point, so `0.1 + 0.2` is `0.30000000000000004`. Compare with a tolerance: `Math.abs(sum - 0.3) < Number.EPSILON`.',
  },
];

const TOKEN = /(\/\/.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+(?:\.\d+)?\b)|(\b(?:const|let|var|function|return|if|for|new)\b)|(\b[A-Za-z_$][\w$]*)(?=\()/g;

/** Tiny syntax highlighter: returns DOM nodes (no innerHTML). */
function highlight(line) {
  const frag = document.createDocumentFragment();
  let last = 0;
  line.replace(TOKEN, (match, comment, str, num, kw, fn, offset) => {
    if (offset > last) frag.append(line.slice(last, offset));
    const span = document.createElement('span');
    span.className = comment ? 'tk-c' : str ? 'tk-s' : num ? 'tk-n' : kw ? 'tk-k' : 'tk-f';
    span.textContent = match;
    frag.append(span);
    last = offset + match.length;
    return match;
  });
  if (last < line.length) frag.append(line.slice(last));
  return frag;
}

/** `code` → <code> without innerHTML */
function richText(text) {
  const frag = document.createDocumentFragment();
  text.split('`').forEach((part, i) => {
    if (i % 2) {
      const c = document.createElement('code');
      c.textContent = part;
      frag.append(c);
    } else frag.append(part);
  });
  return frag;
}

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

export function mount(root) {
  const state = { level: 'easy', list: [], index: 0, score: 0, answered: false, finished: false };
  const wrap = el('div', 'bh');
  root.replaceChildren(wrap);

  function questionsFor(level) {
    return QUESTIONS.filter((q) => q.level === level);
  }

  function start(level = state.level) {
    state.level = level;
    state.list = questionsFor(level);
    state.index = 0;
    state.score = 0;
    state.answered = false;
    state.finished = false;
    render();
  }

  function header() {
    const top = el('div', 'bh-top');
    const levels = el('div', 'bh-levels');
    levels.setAttribute('role', 'group');
    levels.setAttribute('aria-label', 'Difficulty');
    ['easy', 'medium'].forEach((lvl) => {
      const b = el('button', 'bh-level', lvl === 'easy' ? 'Easy' : 'Medium');
      b.type = 'button';
      b.dataset.level = lvl;
      b.setAttribute('aria-pressed', String(state.level === lvl));
      b.addEventListener('click', () => start(lvl));
      levels.append(b);
    });
    const score = el('div', 'bh-score');
    score.append('Score ');
    const b = el('b', null, `${state.score}`);
    b.dataset.role = 'score';
    score.append(b, ` / ${state.list.length}`);
    top.append(levels, score);

    const bar = el('div', 'bh-bar');
    bar.setAttribute('role', 'progressbar');
    bar.setAttribute('aria-label', 'Progress');
    bar.setAttribute('aria-valuemin', '0');
    bar.setAttribute('aria-valuemax', String(state.list.length));
    const done = state.finished ? state.list.length : state.index + (state.answered ? 1 : 0);
    bar.setAttribute('aria-valuenow', String(done));
    const fill = document.createElement('i');
    fill.style.width = `${(done / state.list.length) * 100}%`;
    bar.append(fill);
    return [top, bar];
  }

  function render() {
    wrap.replaceChildren(...header());
    if (state.finished) return renderEnd();

    const q = state.list[state.index];
    wrap.append(el('p', 'bh-q', `Question ${state.index + 1} of ${state.list.length} — ${q.prompt}`));

    const editor = el('div', 'bh-editor');
    const bar = el('div', 'bh-editor-bar');
    bar.append(document.createElement('i'), document.createElement('i'), document.createElement('i'), el('span', null, 'snippet.js'));
    const pre = el('div', 'bh-code');
    pre.setAttribute('role', 'group');
    pre.setAttribute('aria-label', 'Code. Choose the line that contains the bug.');
    q.code.forEach((text, i) => {
      const line = el('button', 'bh-line');
      line.type = 'button';
      line.dataset.line = String(i + 1);
      line.setAttribute('aria-label', `Line ${i + 1}: ${text.trim()}`);
      const no = el('span', 'bh-no', String(i + 1));
      no.setAttribute('aria-hidden', 'true');
      const code = el('span', 'bh-text');
      code.setAttribute('aria-hidden', 'true');
      code.append(highlight(text) || '');
      if (!text) code.textContent = ' ';
      line.append(no, code);
      line.addEventListener('click', () => answer(i + 1));
      pre.append(line);
    });
    pre.addEventListener('keydown', onCodeKey);
    editor.append(bar, pre);
    wrap.append(editor);

    const live = el('div', 'bh-live');
    live.id = 'bh-live';
    live.setAttribute('role', 'status');
    live.setAttribute('aria-live', 'polite');
    wrap.append(live);
    wrap.append(el('p', 'bh-hint', 'Click a line, or focus the code and use ↑ ↓ and Enter. Keys 1–9 pick a line.'));
  }

  function onCodeKey(e) {
    const lines = Array.from(wrap.querySelectorAll('.bh-line'));
    const i = lines.indexOf(document.activeElement);
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const next = lines[(Math.max(i, 0) + (e.key === 'ArrowDown' ? 1 : -1) + lines.length) % lines.length];
      next.focus();
    } else if (/^[1-9]$/.test(e.key) && lines[Number(e.key) - 1]) {
      lines[Number(e.key) - 1].focus();
      answer(Number(e.key));
    }
  }

  function answer(lineNo) {
    if (state.answered || state.finished) return;
    state.answered = true;
    const q = state.list[state.index];
    const correct = lineNo === q.bug;
    if (correct) state.score += 1;

    wrap.querySelectorAll('.bh-line').forEach((node) => {
      const n = Number(node.dataset.line);
      node.setAttribute('aria-disabled', 'true');
      node.tabIndex = -1;
      if (n === q.bug) node.classList.add('is-correct');
      else if (n === lineNo) node.classList.add('is-wrong');
    });

    const fb = el('div', `bh-feedback ${correct ? 'ok' : 'no'}`);
    const head = el('strong', null, correct ? '✅ Correct!' : `❌ Not quite — the bug is on line ${q.bug}.`);
    const body = el('span');
    body.append(richText(q.explain));
    fb.append(head, body);

    const isLast = state.index === state.list.length - 1;
    const next = el('button', 'pg-btn', isLast ? 'See results' : 'Next question');
    next.type = 'button';
    next.dataset.role = 'next';
    next.addEventListener('click', () => {
      if (isLast) state.finished = true;
      else {
        state.index += 1;
        state.answered = false;
      }
      render();
      const target = wrap.querySelector('.bh-line') || wrap.querySelector('[data-role="again"]');
      if (target) target.focus({ preventScroll: true });
    });
    const actions = el('div', 'bh-actions');
    actions.append(next);

    wrap.querySelector('.bh-editor').after(fb, actions);
    const score = wrap.querySelector('[data-role="score"]');
    if (score) score.textContent = String(state.score);
    const done = state.index + 1;
    const fill = wrap.querySelector('.bh-bar > i');
    if (fill) fill.style.width = `${(done / state.list.length) * 100}%`;
    wrap.querySelector('.bh-bar').setAttribute('aria-valuenow', String(done));
    const live = wrap.querySelector('#bh-live');
    if (live) live.textContent = correct ? 'Correct.' : `Incorrect. The bug is on line ${q.bug}.`;
    next.focus({ preventScroll: true });
  }

  function renderEnd() {
    const total = state.list.length;
    const box = el('div', 'bh-end');
    const ratio = state.score / total;
    box.append(
      el('h3', null, `You found ${state.score} of ${total} bugs`),
      el('p', null, ratio === 1 ? 'Perfect run. Nothing gets past you.' : ratio >= 0.6 ? 'Nice work. Try the other level or go again.' : 'Good practice. Read the explanations and try again.')
    );
    const actions = el('div', 'bh-actions');
    actions.style.justifyContent = 'center';
    const again = el('button', 'pg-btn', 'Play again');
    again.type = 'button';
    again.dataset.role = 'again';
    again.addEventListener('click', () => {
      start();
      wrap.querySelector('.bh-line')?.focus({ preventScroll: true });
    });
    const other = el('button', 'pg-btn ghost', state.level === 'easy' ? 'Try Medium' : 'Try Easy');
    other.type = 'button';
    other.addEventListener('click', () => start(state.level === 'easy' ? 'medium' : 'easy'));
    actions.append(again, other);
    box.append(actions);
    wrap.append(box);
    again.focus({ preventScroll: true });
  }

  start('easy');
  return {
    pause() {},
    destroy() {
      root.replaceChildren();
    },
    getState: () => ({ ...state }),
  };
}
