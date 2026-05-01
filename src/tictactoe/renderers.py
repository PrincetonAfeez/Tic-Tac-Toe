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

