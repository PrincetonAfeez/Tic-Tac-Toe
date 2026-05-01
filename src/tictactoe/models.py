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

@dataclass(frozen=True)
class Board:
    size: int = 3
    k: int = 3
    cells: tuple[Cell, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.size < 3:
            raise InvalidBoardSizeError("Board size must be at least 3")
        if self.k < 2 or self.k > self.size:
            raise InvalidBoardSizeError("Win length k must be between 2 and board size")
        expected = self.size * self.size
        cells = self.cells or (Player.NONE,) * expected
        if len(cells) != expected:
            raise InvalidBoardSizeError(
                f"Expected {expected} cells for a {self.size}x{self.size} board, got {len(cells)}"
            )
        normalized = tuple(Player.from_value(cell) for cell in cells)
        object.__setattr__(self, "cells", normalized)

    @classmethod
    def empty(cls, size: int = 3, k: int | None = None) -> Board:
        win_length = 3 if k is None else k
        return cls(size=size, k=win_length)

    def index(self, position: Position) -> int:
        return position.to_index(self.size)

    def at(self, position: Position) -> Cell:
        return self.cells[self.index(position)]

    def place(self, player: Player, position: Position) -> Board:
        if player is Player.NONE:
            msg = "Player.NONE cannot be placed on the board"
            raise ValueError(msg)
        index = self.index(position)
        if self.cells[index] is not Player.NONE:
            raise CellOccupiedError(f"Cell {position} is already occupied")
        cells = list(self.cells)
        cells[index] = player
        return Board(size=self.size, k=self.k, cells=tuple(cells))

    @property
    def filled_count(self) -> int:
        return sum(cell is not Player.NONE for cell in self.cells)

    @property
    def is_full(self) -> bool:
        return self.filled_count == len(self.cells)

    def positions(self) -> tuple[Position, ...]:
        return tuple(Position.from_index(index, self.size) for index in range(self.size * self.size))

    def rows(self) -> tuple[tuple[Cell, ...], ...]:
        return tuple(
            self.cells[row * self.size : (row + 1) * self.size] for row in range(self.size)
        )

    def __str__(self) -> str:
        return format(self, "grid")

    def __format__(self, spec: str) -> str:
        spec = spec or "grid"
        if spec == "compact":
            return "|".join("".join(cell.value for cell in row) for row in self.rows())
        if spec == "numbered":
            width = len(str(self.size * self.size))
            rows: list[str] = []
            for row in range(self.size):
                parts = []
                for col in range(self.size):
                    pos = Position(row, col)
                    cell = self.at(pos)
                    text = str(pos.to_index(self.size) + 1) if cell is Player.NONE else cell.value
                    parts.append(text.rjust(width))
                rows.append(" ".join(parts))
            return "\n".join(rows)
        if spec == "grid":
            rows = []
            separator = "\n" + "+".join(["---"] * self.size) + "\n"
            for board_row in self.rows():
                rows.append(" " + " | ".join(cell.value for cell in board_row) + " ")
            return separator.join(rows)
        msg = f"Unknown Board format spec {spec!r}"
        raise ValueError(msg)

@dataclass(frozen=True)
class GameState:
    board: Board = field(default_factory=Board)
    next_player: Player = Player.X
    history: tuple[Move, ...] = field(default_factory=tuple)
    outcome: Outcome = Outcome.IN_PROGRESS
    winning_line: WinCondition | None = None
    misere: bool = False
    started_at: float = field(default_factory=monotonic)

    @classmethod
    def new(cls, size: int = 3, k: int | None = None, *, misere: bool = False) -> GameState:
        return cls(board=Board.empty(size=size, k=3 if k is None else k), misere=misere)

    @property
    def move_count(self) -> int:
        return len(self.history)

    @property
    def is_over(self) -> bool:
        return self.outcome.is_terminal