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

def state_from_dict(data: dict[str, Any]) -> GameState:
    board_data = data["board"]
    board = Board(
        size=int(board_data["size"]),
        k=int(board_data["k"]),
        cells=tuple(Player.from_value(cell) for cell in board_data["cells"]),
    )
    history = tuple(
        Move(
            player=Player.from_value(item["player"]),
            position=Position(int(item["row"]), int(item["col"])),
            timestamp=float(item["timestamp"]),
            move_number=int(item["move_number"]),
        )
        for item in data.get("history", [])
    )
    line_data = data.get("winning_line")
    winning_line = None
    if line_data is not None:
        winning_line = WinCondition(
            player=Player.from_value(line_data["player"]),
            positions=tuple(
                Position(int(item["row"]), int(item["col"])) for item in line_data["positions"]
            ),
        )
    return GameState(
        board=board,
        next_player=Player.from_value(data["next_player"]),
        history=history,
        outcome=Outcome(data["outcome"]),
        winning_line=winning_line,
        misere=bool(data.get("misere", False)),
        started_at=float(data.get("started_at", 0.0)),
    )

class GameRepository(ABC):
    @abstractmethod
    def save(
        self,
        state: GameState,
        *,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:

    @abstractmethod
    def load(self, path_or_name: str | Path) -> GameState:

    @abstractmethod
    def list(self) -> list[Path]:

    @abstractmethod
    def delete(self, path_or_name: str | Path) -> None:


@dataclass
class JsonGameRepository(GameRepository):
    root: Path = APP_DIR / "saves"

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        state: GameState,
        *,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = _safe_stem(name or f"{stamp}-{state.board.size}x{state.board.size}")
        path = self.root / f"{stem}.json"
        if path.exists():
            path = self.root / f"{stem}-{stamp}.json"
        path.write_text(json.dumps(state_to_dict(state, metadata), indent=2), encoding="utf-8")
        return path

    def load(self, path_or_name: str | Path) -> GameState:
        path = self._resolve(path_or_name)
        return state_from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[Path]:
        return sorted(self.root.glob("*.json"))

    def delete(self, path_or_name: str | Path) -> None:
        self._resolve(path_or_name).unlink()

    def _resolve(self, path_or_name: str | Path) -> Path:
        path = Path(path_or_name).expanduser()
        if path.exists():
            return path
        candidate = self.root / path
        if candidate.exists():
            return candidate
        if candidate.suffix != ".json":
            candidate = candidate.with_suffix(".json")
            if candidate.exists():
                return candidate
        raise FileNotFoundError(path_or_name)

class InMemoryGameRepository(GameRepository):
    def __init__(self) -> None:
        self._games: dict[str, dict[str, Any]] = {}

    def save(
        self,
        state: GameState,
        *,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        stem = _safe_stem(name or f"game-{len(self._games) + 1}")
        self._games[stem] = state_to_dict(state, metadata)
        return Path(stem)

    def load(self, path_or_name: str | Path) -> GameState:
        stem = Path(path_or_name).stem
        return state_from_dict(self._games[stem])

    def list(self) -> list[Path]:
        return [Path(key) for key in sorted(self._games)]

    def delete(self, path_or_name: str | Path) -> None:
        del self._games[Path(path_or_name).stem]

