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
