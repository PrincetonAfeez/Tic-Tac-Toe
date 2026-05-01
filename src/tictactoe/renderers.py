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
