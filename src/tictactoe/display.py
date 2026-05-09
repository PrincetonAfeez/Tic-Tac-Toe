"""Terminal display owner for renderer output."""

from __future__ import annotations

import sys

from . import ansi
from .models import GameState
from .renderers import Renderer


class Display:
    def __init__(self, renderer: Renderer, *, clear_each_frame: bool = False) -> None:
        self.renderer = renderer
        self.clear_each_frame = clear_each_frame
        self._last_frame: str | None = None

    def render(self, state: GameState) -> str:
        return self.renderer.render(state)

    def draw(self, state: GameState) -> None:
        frame = self.render(state)
        if frame == self._last_frame:
            return
        if self.clear_each_frame:
            sys.stdout.write(ansi.clear())
        print(frame)
        self._last_frame = frame

