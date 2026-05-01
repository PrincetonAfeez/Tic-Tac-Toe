from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import ClassVar

from .exceptions import CellOccupiedError, InvalidBoardSizeError, OutOfBoundsError

class Player(Enum):
    X = "X"
    O = "O"
    NONE = "."

    @property
    def opponent(self) -> Player:
        if self is Player.X:
            return Player.O
        if self is Player.O:
            return Player.X
        return Player.NONE

    @property
    def is_mark(self) -> bool:
        return self is not Player.NONE

    @classmethod
    def from_value(cls, value: str | Player) -> Player:
        if isinstance(value, Player):
            return value
        normalized = value.strip().upper()
        if normalized in {"", ".", "NONE", "-"}:
            return Player.NONE
        return Player(normalized)


Cell = Player

class Outcome(Enum):
    IN_PROGRESS = "in_progress"
    X_WINS = "x_wins"
    O_WINS = "o_wins"
    DRAW = "draw"
    ABANDONED = "abandoned"

    @property
    def winner(self) -> Player | None:
        if self is Outcome.X_WINS:
            return Player.X
        if self is Outcome.O_WINS:
            return Player.O
        return None

    @property
    def is_terminal(self) -> bool:
        return self is not Outcome.IN_PROGRESS

    @classmethod
    def for_winner(cls, player: Player) -> Outcome:
        if player is Player.X:
            return Outcome.X_WINS
        if player is Player.O:
            return Outcome.O_WINS
        msg = "Player.NONE cannot win"
        raise ValueError(msg)

