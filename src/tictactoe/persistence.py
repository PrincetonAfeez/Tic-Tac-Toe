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

def state_to_dict(state: GameState, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "version": 1,
        "metadata": metadata or {},
        "board": {
            "size": state.board.size,
            "k": state.board.k,
            "cells": [cell.value for cell in state.board.cells],
        },
        "next_player": state.next_player.value,
        "history": [
            {
                "player": move.player.value,
                "row": move.position.row,
                "col": move.position.col,
                "timestamp": move.timestamp,
                "move_number": move.move_number,
            }
            for move in state.history
        ],
        "outcome": state.outcome.value,
        "winning_line": None
        if state.winning_line is None
        else {
            "player": state.winning_line.player.value,
            "positions": [
                {"row": position.row, "col": position.col}
                for position in state.winning_line.positions
            ],
        },
        "misere": state.misere,
        "started_at": state.started_at,
    }
