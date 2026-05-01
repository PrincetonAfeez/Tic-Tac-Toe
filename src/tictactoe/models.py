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

