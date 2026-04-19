from __future__ import annotations

import sys
from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_STR = str(_BACKEND_ROOT)
if _BACKEND_STR not in sys.path:
    sys.path.insert(0, _BACKEND_STR)
