# Tic-Tac-Toe

An immutable, testable Tic-Tac-Toe project with a real CLI, multiple AI agents, generalized board sizes, JSON saves, replay, analysis, and tournament mode.

The important design choice is that game state never mutates. A move returns a new `GameState`; the old one remains available for undo, replay, AI search, and tests.

**Requirements:** Python 3.11 or newer (see `requires-python` in `pyproject.toml`). Runtime dependencies: none beyond the standard library.

## Install

From this directory:

```powershell
python -m pip install -e .
```

For tests, linters, and type checking, use the optional dev extra:

```powershell
python -m pip install -e ".[dev]"
```

Then run:

```powershell
tictactoe --help
tictactoe play --x human --o minimax
```

Without installing, use:

```powershell
$env:PYTHONPATH = "src"
python -m tictactoe --help
```

## Quick Examples

```powershell
tictactoe play
tictactoe play --x human --o minimax --renderer coordinate
tictactoe play --x human --o minimax-medium --size 4 --k 3
tictactoe play --x human --o heuristic --misere
tictactoe watch --x minimax --o mcts --size 4 --k 3 --delay 0.25
tictactoe tournament --x minimax --o random --games 100
tictactoe replay center-game.json
tictactoe analyze center-game.json
tictactoe stats
```

## Features

- Immutable `Board`, `GameState`, `Move`, `Position`, and `WinCondition` dataclasses.
- `Player`, `Cell`, and `Outcome` enums with explicit terminal outcomes.
- Pure engine functions: `make_move`, `available_moves`, `check_winner`, `undo`, and `replay`.
- Generalized `NxN` boards with configurable `k` in a row to win.
- Misère mode, where making the line loses.
- Human, random, heuristic, minimax, and Monte Carlo rollout (`mcts`) agents.
- Minimax uses alpha-beta pruning and memoization.
- Renderers: classic, coordinate, minimal, and big.
- JSON save/load under `~/.tictactoe/saves`.
- Replay and post-game minimax analysis commands.
- Tournament mode for batch AI comparisons.
- Persistent aggregate stats under `~/.tictactoe/stats.json`.
- Example and **Hypothesis** property tests; CI runs **pytest**, **Ruff**, and **Mypy** on Python 3.11–3.13 (see `.github/workflows/ci.yml`).

## In-Game Commands

| Command | Action |
| --- | --- |
| `A1`, `1A`, `row,col` | Place a move by coordinate |
| `1` to `9` | Place a move by keypad layout on 3x3 |
| `hint` | Ask minimax for a recommended move |
| `u` | Undo two plies, or one if only one move exists |
| `r` | Restart the current match |
| `s` | Save the current game |
| `l` | Load a saved game |
| `h` or `?` | Show help |
| `q` | Quit, with an optional save prompt |

## Configuration

Optional config lives at:

```text
~/.tictactoe/config.toml
```

Example:

```toml
[board]
size = 3
k = 3
misere = false

[display]
renderer = "classic"
colors = "classic"
no_color = false

[agents]
x = "human"
o = "minimax"

[input]
mode = "keypad"

[ai]
minimax_depth = 4
mcts_simulations = 300
```

Precedence is CLI flags, then config, then built-in defaults.

## Development

### Tests

With dev dependencies installed, **pytest** adds `src` to the import path via `pyproject.toml`:

```powershell
python -m pytest
```

The standard library runner does not read that setting; the `tests` package prepends `src` on import so discovery works from the repo root without `PYTHONPATH`:

```powershell
python -m unittest discover -s tests -t .
```

(`-t .` is the project top level so `tests` is treated as an importable package.)

After `pip install -e ".[dev]"`, imports resolve for other tools without either hook.

### Lint and types

```powershell
ruff check src tests
mypy src
```

These commands match what runs in GitHub Actions on every push and pull request.

## Further reading

- `ARCHITECTURE.md` — module layout and design notes.
- `ALGORITHMS.md` — minimax and Monte Carlo rollout behavior.
