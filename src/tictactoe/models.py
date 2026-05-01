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

@dataclass(frozen=True, order=True)
class Position:
    row: int
    col: int

    ROW_LABELS: ClassVar[str] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __post_init__(self) -> None:
        if self.row < 0 or self.col < 0:
            raise OutOfBoundsError(f"Position must be non-negative, got ({self.row}, {self.col})")

    def to_index(self, size: int) -> int:
        if self.row >= size or self.col >= size:
            raise OutOfBoundsError(f"{self} is outside a {size}x{size} board")
        return self.row * size + self.col

    @classmethod
    def from_index(cls, index: int, size: int) -> Position:
        if index < 0 or index >= size * size:
            raise OutOfBoundsError(f"Index {index} is outside a {size}x{size} board")
        return cls(index // size, index % size)

    @property
    def label(self) -> str:
        row = self.ROW_LABELS[self.row] if self.row < len(self.ROW_LABELS) else f"R{self.row + 1}"
        return f"{row}{self.col + 1}"

    def __str__(self) -> str:
        return self.label


@dataclass(frozen=True)
class WinCondition:
    player: Player
    positions: tuple[Position, ...]

    def __post_init__(self) -> None:
        if self.player is Player.NONE:
            msg = "A winning line must belong to X or O"
            raise ValueError(msg)
        object.__setattr__(self, "positions", tuple(self.positions))

    def contains(self, position: Position) -> bool:
        return position in self.positions

@dataclass(frozen=True)
class Move:
    player: Player
    position: Position
    timestamp: float
    move_number: int

    @classmethod
    def create(cls, player: Player, position: Position, move_number: int) -> Move:
        return cls(player=player, position=position, timestamp=monotonic(), move_number=move_number)

