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

