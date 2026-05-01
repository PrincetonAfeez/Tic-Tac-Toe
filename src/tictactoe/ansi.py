"""Tiny ANSI helper module used by renderers and the display."""

from __future__ import annotations

import os

CSI = "\033["


def enabled(no_color: bool = False) -> bool:
    return not no_color and "NO_COLOR" not in os.environ


def style(text: str, *codes: str, enabled_: bool = True) -> str:
    if not enabled_ or not codes:
        return text
    return f"{CSI}{';'.join(codes)}m{text}{CSI}0m"


def clear() -> str:
    return f"{CSI}2J{CSI}H"


def move(row: int, col: int) -> str:
    return f"{CSI}{row};{col}H"


def hide_cursor() -> str:
    return f"{CSI}?25l"


def show_cursor() -> str:
    return f"{CSI}?25h"

