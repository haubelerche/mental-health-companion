"""Pytest setup for backend/tests: PYTHONPATH, repo-root .env, collection rules."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_THIS = Path(__file__).resolve().parent
_BACKEND_ROOT = _THIS.parent
_REPO_ROOT = _BACKEND_ROOT.parent

# `app.*` resolves from backend/; `scripts.*` from repo root.
for _p in (_BACKEND_ROOT, _REPO_ROOT):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# Manual wire script (imports legacy paths); not a pytest suite.
collect_ignore = ["test_db.py"]


def pytest_configure(config: pytest.Config) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_REPO_ROOT / ".env", override=False)
