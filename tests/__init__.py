"""Test package with ``src`` on ``sys.path`` for ``unittest discover``."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_src = _root / "src"
_s = str(_src)
if _s not in sys.path:
    sys.path.insert(0, _s)
