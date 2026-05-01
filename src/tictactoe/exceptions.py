"""Custom exception hierarchy for the game engine."""


class GameError(Exception):
    """Base class for domain errors raised by the game."""


class InvalidMoveError(GameError):
    """Raised when a move cannot be applied to a state."""


class CellOccupiedError(InvalidMoveError):
    """Raised when a move targets an occupied cell."""


class OutOfBoundsError(InvalidMoveError):
    """Raised when a position is not on the board."""


class GameOverError(InvalidMoveError):
    """Raised when a move is attempted after the game has ended."""


class InvalidBoardSizeError(GameError):
    """Raised when a board size or win length is invalid."""

