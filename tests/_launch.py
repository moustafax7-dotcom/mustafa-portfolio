"""Shared Playwright launch options.
By default Playwright uses its own bundled Chromium. If that is not installed (e.g. in a
restricted sandbox) point CHROMIUM_PATH at any Chromium/Chrome binary:
    CHROMIUM_PATH=/path/to/chrome python3 tests/features.py
"""
import os

def launch_kwargs():
    path = os.environ.get('CHROMIUM_PATH')
    if not path:
        return {}
    return {'executable_path': path, 'args': ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']}


# Newer Playwright versions dispatch one trusted pointer/mouse move at (0,0) when a page opens. That is
# not a real pointer move, so tests that check "cursor stays dormant until the first real mouse move"
# install this init script to swallow those synthetic events.
IGNORE_SYNTHETIC_MOVE = """
['pointermove', 'mousemove'].forEach(type => addEventListener(type, e => {
  if (e.clientX || e.clientY) { window.__realMove = true; return; }
  if (!window.__realMove) e.stopImmediatePropagation();
}, true));
"""
