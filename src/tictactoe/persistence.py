from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from .config import APP_DIR
from .models import Board, GameState, Move, Outcome, Player, Position, WinCondition

def _safe_stem(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", text.strip()).strip("-")
    return cleaned or "game"

