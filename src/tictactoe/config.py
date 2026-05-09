"""Configuration loading with CLI-over-config-over-default precedence."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


APP_DIR = Path.home() / ".tictactoe"
CONFIG_PATH = APP_DIR / "config.toml"

DEFAULT_CONFIG: dict[str, Any] = {
    "board": {"size": 3, "k": 3, "misere": False},
    "display": {"renderer": "classic", "colors": "classic", "no_color": False},
    "agents": {"x": "human", "o": "minimax"},
    "input": {"mode": "keypad"},
    "ai": {"minimax_depth": None, "mcts_simulations": 200},
}


def load_config(path: Path | None = None) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    config_path = path or CONFIG_PATH
    if config_path.exists():
        if tomllib is None:
            raise RuntimeError("tomllib is required to read config files")
        loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
        _deep_update(config, loaded)
    return config


def _deep_update(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value

