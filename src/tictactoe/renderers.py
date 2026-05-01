from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from . import ansi
from .models import GameState, Outcome, Player, Position

@dataclass(frozen=True)
class ColorScheme:
    name: str
    x: str
    o: str
    highlight: str
    dim: str = "2"

    @classmethod
    def from_name(cls, name: str) -> ColorScheme:
        try:
            return COLOR_SCHEMES[name]
        except KeyError as exc:
            choices = ", ".join(sorted(COLOR_SCHEMES))
            raise ValueError(f"Unknown color scheme {name!r}. Choices: {choices}") from exc


COLOR_SCHEMES: dict[str, ColorScheme] = {
    "classic": ColorScheme("classic", x="31;1", o="34;1", highlight="42;30;1"),
    "monochrome": ColorScheme("monochrome", x="", o="", highlight="7"),
    "colorblind": ColorScheme("colorblind", x="35;1", o="36;1", highlight="43;30;1"),
}


class Renderer(ABC):
    @abstractmethod
    def render(self, state: GameState) -> str:


def outcome_text(state: GameState) -> str:
    if state.outcome is Outcome.IN_PROGRESS:
        return f"Turn: {state.next_player.value}"
    if state.outcome is Outcome.DRAW:
        return "Draw"
    if state.outcome is Outcome.ABANDONED:
        return "Abandoned"
    winner = state.outcome.winner
    assert winner is not None
    if state.misere and state.winning_line is not None:
        loser = state.winning_line.player
        return f"{winner.value} wins; {loser.value} made the line"
    return f"{winner.value} wins"

def _history_text(state: GameState, limit: int = 5) -> str:
    if not state.history:
        return "History: empty"
    moves = "  ".join(
        f"{move.move_number}.{move.player.value}@{move.position}" for move in state.history[-limit:]
    )
    prefix = "History"
    if len(state.history) > limit:
        prefix += f" (last {limit})"
    return f"{prefix}: {moves}"

class ClassicRenderer(Renderer):
    def __init__(
        self,
        *,
        color_scheme: ColorScheme | None = None,
        no_color: bool = False,
        show_coordinates: bool = True,
    ) -> None:
        self.color_scheme = color_scheme or COLOR_SCHEMES["classic"]
        self.use_color = ansi.enabled(no_color)
        self.show_coordinates = show_coordinates

    def render(self, state: GameState) -> str:
        board = state.board
        width = max(3, len(str(board.size)))
        header = " " * 4 + " ".join(f"{col + 1:^{width}}" for col in range(board.size))
        rows: list[str] = []
        for row in range(board.size):
            parts = []
            for col in range(board.size):
                position = Position(row, col)
                parts.append(f"{self._cell_text(state, position):^{width}}")
            label = Position.ROW_LABELS[row] if row < len(Position.ROW_LABELS) else str(row + 1)
            rows.append(f"{label:>2}  " + " | ".join(parts))
        separator = "    " + "-+-".join("-" * width for _ in range(board.size))
        board_text = f"\n{separator}\n".join(rows)
        if self.show_coordinates:
            board_text = f"{header}\n{board_text}"
        return "\n".join(
            [
                board_text,
                "",
                f"{outcome_text(state)}  |  Moves: {state.move_count}  |  Board: {board.size}x{board.size}, k={board.k}",
                _history_text(state),
            ]
        )
