# Architecture Decision Record

## App 36 — Tic Tac Toe
**Game Systems Group | Document 1 of 5**

**Status:** Accepted  
**Date:** 2026-05-09  
**Project:** `tictactoe-princ` / `tictactoe`

---

## ADR-001: Use Immutable Domain Objects as the Core Game Invariant

### Status
Accepted

### Context
The project is not only a playable Tic-Tac-Toe CLI. It also supports undo, replay, AI search, JSON saves, analysis, generalized board sizes, and tournament mode. Those features all depend on being able to trust previous game states. If a board can be mutated in place, then undo can accidentally expose changed objects, AI agents can corrupt the state they are evaluating, saved histories can drift from rendered boards, and tests become harder to reason about.

The repository explicitly identifies immutable state as the central design choice: a move returns a new `GameState`, while the previous state remains available for undo, replay, AI, and tests.

### Decision Drivers
- Preserve authorship integrity through clear, inspectable Python data structures.
- Make AI search safe by preventing child branches from mutating parent boards.
- Make undo and replay simple consequences of stored move history.
- Keep the game engine pure and deterministic enough for unit and property tests.
- Support larger roadmap complexity without relying on hidden global state.

### Options Considered
1. **Mutable board object updated in place.**  
   Simple for a tiny 3x3 CLI, but dangerous for undo, replay, minimax, and tests.

2. **Mutable board plus explicit copy before every risky operation.**  
   Safer than raw mutation, but correctness depends on every caller remembering to copy.

3. **Frozen dataclasses for board, moves, positions, win conditions, and game state.**  
   More object creation, but makes the invariant obvious and enforceable.

### Decision
Use frozen dataclasses for the core model: `Board`, `GameState`, `Move`, `Position`, and `WinCondition`. Applying a move produces a new board and a new game state instead of mutating the old objects.

### Rationale
The immutable model fits the expanded feature set better than a classic mutable board. `Board.place()` creates a new `Board`; `make_move()` returns a replacement `GameState`; `undo()` rebuilds state through replay. This allows AI agents to receive a state snapshot and explore future states without defensive copying or shared-state bugs.

### Trade-offs Accepted
- More object allocation than an in-place 3x3 implementation.
- Some functions need to return entire new objects rather than small mutation results.
- Learners must understand `dataclasses.replace`, tuples, and value-object design.

### Consequences
- Undo and replay are natural: keep or replay a prefix of `history`.
- Minimax can key its cache by immutable board state.
- Tests can assert that previous boards remain unchanged after moves.
- JSON persistence can serialize a full state and a move history without worrying that another component mutated it later.

### Superseded By
None.

---

## ADR-002: Keep the Engine Pure and Move I/O to CLI, Display, and Persistence Modules

### Status
Accepted

### Context
Tic-Tac-Toe has a small rule set, but this project adds many modes around the rule engine: human play, AI-vs-AI watch mode, tournaments, saves, replay, statistics, analysis, and multiple renderers. If rule validation, terminal prompts, JSON files, and AI logic were mixed together, the app would become difficult to test and maintain.

### Decision Drivers
- Separation of concerns under Constitution Article 4.
- Testability of core rules without terminal input.
- Reuse of the same engine by CLI, agents, replay, and analysis.
- Clear boundary between domain errors and operating errors.

### Options Considered
1. **Single script with board state, prompts, and rules together.**  
   Fastest to build, but too limited for AI agents and replay.

2. **Object-oriented `Game` class owning rules, display, and persistence.**  
   Encapsulates behavior, but risks becoming a large god object.

3. **Pure engine functions plus separate adapters.**  
   More modules, but cleaner and more testable.

### Decision
Place game rules in `tictactoe.engine` as pure functions:
- `make_move`
- `available_moves`
- `check_winner`
- `undo`
- `replay`
- `abandon`

Terminal display, input handling, save/load, stats, and CLI dispatch are kept in separate modules.

### Rationale
The engine has no reason to know whether a move came from a human prompt, a minimax agent, a replay file, or a tournament loop. Keeping the engine pure makes every mode use the same rule implementation and prevents duplicate game logic.

### Trade-offs Accepted
- CLI functions must coordinate more pieces explicitly.
- The separation introduces additional files and imports.
- Some CLI helpers are procedural rather than encapsulated in a larger runtime class.

### Consequences
- `cmd_replay` and `cmd_analyze` can rebuild games from saved history.
- Tests can exercise rules directly without subprocesses or terminal mocking.
- AI agents can call `make_move`, `available_moves`, and `check_winner` safely.
- Bugs in renderer or persistence code are less likely to corrupt rule correctness.

### Superseded By
None.

---

## ADR-003: Generalize the Board to NxN with Configurable K-in-a-Row

### Status
Accepted

### Context
Classic Tic-Tac-Toe is 3x3 with three in a row, but the project requirements include generalized board sizes. This means the engine cannot hard-code the eight classic winning lines. It must support examples like `--size 4 --k 3` while preserving correctness for the standard game.

### Decision Drivers
- Demonstrate progressive complexity beyond a basic game.
- Avoid duplicated 3x3-specific logic.
- Make win detection work for horizontal, vertical, and both diagonal directions.
- Keep generalized rules reusable by AI agents and tests.

### Options Considered
1. **Hard-code classic 3x3 winning lines only.**  
   Simple, but incompatible with `--size` and `--k`.

2. **Generate all full rows, columns, and diagonals only.**  
   Works for `k == size`, but fails for partial windows like 4x4 with k=3.

3. **Generate every contiguous line segment of length `k`.**  
   More computation, but correct for generalized boards.

### Decision
Use cached line generation in `all_line_positions(size, k)` across four directions: horizontal, vertical, diagonal down-right, and diagonal down-left. `check_winner()` walks those generated lines and checks for a filled line belonging to one player.

### Rationale
This design keeps the rest of the engine unchanged. `Board` validates `size >= 3` and `2 <= k <= size`; line generation handles the board geometry; `check_winner()` remains a straightforward loop.

### Trade-offs Accepted
- Larger boards create more candidate lines.
- The algorithm still scans candidate lines after each move instead of incrementally updating line counts.
- Full minimax becomes expensive on larger boards.

### Consequences
- Classic Tic-Tac-Toe remains a special case of the generalized engine.
- AI agents and renderers do not need separate board-size branches.
- The CLI can expose `--size` and `--k` confidently.
- Minimax depth limiting becomes necessary for boards larger than 3x3.

### Superseded By
None.

---

## ADR-004: Implement Agents as Strategy Objects with a Common `choose_move` Contract

### Status
Accepted

### Context
The project supports human, random, heuristic, minimax, and Monte Carlo rollout agents. Play mode can combine human and AI agents, while watch and tournament modes require AI-only combinations. A single common interface avoids special-case game loops for every agent type.

### Decision Drivers
- Interchangeability between human and AI players.
- Ability to compare agents in tournament mode.
- Testability of each agent independently.
- Avoid coupling the engine to AI implementations.

### Options Considered
1. **Inline AI choices inside CLI command functions.**  
   Simple at first, but would tangle game flow and strategy logic.

2. **One large AI function with mode strings.**  
   Centralized but hard to extend and test.

3. **Agent strategy objects with `choose_move(state) -> Position`.**  
   Modular, testable, and extensible.

### Decision
Define an `Agent` protocol with `choose_move(state: GameState) -> Position`, plus implementations for:
- `HumanAgent`
- `RandomAgent`
- `HeuristicAgent`
- `MinimaxAgent`
- `MonteCarloRolloutAgent` / CLI name `mcts`

### Rationale
The shared strategy shape lets the CLI select an agent by name, lets tournaments instantiate fresh agents with deterministic seeds, and lets tests assert legal move behavior for each agent class. Human input is still represented as an agent, but it accepts injectable `read_line` and `echo` functions for testing.

### Trade-offs Accepted
- `HumanAgent` still performs interactive input, so it is not pure like the AI agents.
- Agent randomness requires seeded `random.Random` objects for reproducible tests.
- The term `mcts` is user-friendly but slightly imprecise because the implementation is flat Monte Carlo rollout, not full UCT.

### Consequences
- `watch` and `tournament` can reject human agents while reusing the same creation path.
- Minimax, heuristic, and Monte Carlo can be compared without changing engine code.
- `last_stats` gives the CLI a place to report search effort.
- Future agents can be added by extending `create_agent()` and `AGENT_NAMES`.

### Superseded By
None.

---

## ADR-005: Use Minimax with Alpha-Beta Pruning and Memoization for Strong Play

### Status
Accepted

### Context
A Tic-Tac-Toe project with AI agents needs at least one strong deterministic strategy. Random and heuristic agents are useful baselines, but a strong agent demonstrates search, recursion, scoring, pruning, and state memoization.

### Decision Drivers
- Provide optimal play on classic 3x3 boards.
- Keep the algorithm understandable for an academic Python project.
- Support larger boards through optional depth limits.
- Reuse immutable board states for memoization keys.

### Options Considered
1. **Only random and heuristic agents.**  
   Simpler, but limited as evidence of algorithmic depth.

2. **Full minimax without pruning.**  
   Correct but slower and less instructive.

3. **Minimax with alpha-beta pruning and memoization.**  
   Stronger and still teachable.

4. **Full UCT Monte Carlo Tree Search.**  
   More advanced, but too much scope for this project stage.

### Decision
Implement `MinimaxAgent` with alpha-beta pruning, a local memoization dictionary keyed by immutable board state and search parameters, depth-aware terminal scoring, and heuristic scoring at depth-limited leaves.

### Rationale
Classic 3x3 Tic-Tac-Toe is small enough for full minimax, and generalized boards can use a depth limit. Memoization works cleanly because `Board` is immutable and hashable. Depth-aware scoring encourages faster wins and slower losses.

### Trade-offs Accepted
- Minimax can still be expensive on larger boards.
- The heuristic leaf evaluator is not a proof of optimal play beyond full-depth classic boards.
- Caching is per move search, not a persistent cross-game transposition table.

### Consequences
- `minimax` should not lose in classic play when given sufficient depth.
- `minimax-medium` and automatic larger-board depth limits make generalized mode practical.
- The `analyze` command can use minimax as an advisor over saved move histories.
- Search statistics can be displayed after AI moves.

### Superseded By
None.

---

## ADR-006: Persist Saves and Aggregate Stats as JSON Under the User Home Directory

### Status
Accepted

### Context
The project supports saving/loading games, replay, analysis, and persistent agent statistics. These features require durable state, but the project should remain standard-library only and easy to inspect.

### Decision Drivers
- No runtime dependencies.
- Human-readable saved game files.
- Easy debugging and manual inspection.
- Stable enough contract for replay and analysis.

### Options Considered
1. **In-memory saves only.**  
   Useful for tests, but not useful to users.

2. **Pickle serialization.**  
   Easy, but opaque and less safe.

3. **SQLite database.**  
   Powerful, but too heavy for this project.

4. **JSON game saves and JSON/JSONL stats files.**  
   Inspectable, simple, and standard-library only.

### Decision
Use `JsonGameRepository` for game saves under `~/.tictactoe/saves`, `stats.json` for aggregate agent stats, and `history.jsonl` for completed game events. Provide `InMemoryGameRepository` for tests.

### Rationale
JSON is a good match for a learner CLI app: it preserves structure, supports replay and analysis, and can be edited or inspected manually. JSONL is appropriate for append-only history.

### Trade-offs Accepted
- No database-level locking or transactions.
- No formal schema migration beyond a `version` field in save payloads.
- Large histories could grow without rotation.

### Consequences
- Replay and analysis commands can accept save names or paths.
- Stats survive across CLI runs.
- Tests can use in-memory repositories instead of touching the real home directory.
- Future versions should treat save schema compatibility as a maintenance concern.

### Superseded By
None.

---

## ADR-007: Keep Renderers Pure and Put Terminal Ownership in `Display`

### Status
Accepted

### Context
The app has several render styles: classic, coordinate, minimal, and big. It also supports ANSI colors, highlight lines, and optional frame clearing. If renderers printed directly, they would be harder to test and harder to reuse for replay, snapshots, and minimal output.

### Decision Drivers
- Testable state-to-string rendering.
- Separation between formatting and terminal side effects.
- Support multiple renderer strategies.
- Respect `NO_COLOR` and `--no-color`.

### Options Considered
1. **Render by printing directly from engine/CLI.**  
   Easy but not testable as pure output.

2. **One renderer with many flags.**  
   Compact but less clear as styles grow.

3. **Renderer strategy classes plus a display owner.**  
   Slightly more structure, but clean boundaries.

### Decision
Implement renderers as classes with `render(state) -> str`; put actual printing and optional terminal clearing in `Display.draw()`.

### Rationale
Rendering is a classic strategy boundary. The CLI can ask for a renderer by name, and the `Display` can avoid redundant redraws without each renderer knowing about stdout.

### Trade-offs Accepted
- More classes than a simple board-print function.
- Some style features, such as colors and highlights, require coordination between renderer and ANSI helper.

### Consequences
- Minimal renderer works well for scripts and tests.
- Coordinate renderer supports human move entry.
- Big renderer gives a richer terminal mode without changing engine logic.
- Display can clear frames or suppress duplicate output.

### Superseded By
None.

---

## ADR-008: Treat This as a Medium Roadmap Project, Not a 24-Hour Micro Utility

### Status
Accepted

### Context
This project goes beyond the smallest CLI exercises. It includes an immutable model, generalized rules, multiple AI agents, CLI modes, persistent JSON saves, replay, analysis, tournaments, renderers, and test coverage. Under the Constitution, that scope needs to be justified rather than treated as a small one-file utility.

### Decision Drivers
- Constitution Article 3: scope discipline.
- Constitution Amendment 3.4: medium projects may take 2–5 days.
- Constitution Article 7: progression should show increased complexity.
- Keep complexity intentional rather than accidental.

### Options Considered
1. **Reduce to a simple 3x3 human-vs-human game.**  
   Good beginner scope, but not aligned with App 36 progression.

2. **Build a full game framework with GUI/network play.**  
   Too much scope.

3. **Build a terminal game with focused AI, persistence, and analysis features.**  
   Larger but still bounded.

### Decision
Treat App 36 as a medium CLI/game project. Keep the feature set limited to terminal interaction, standard-library persistence, deterministic engine rules, and a defined agent family.

### Rationale
The project demonstrates meaningful architectural growth while avoiding GUI, network play, external databases, and multiplayer services. It is bigger than a micro app but still proportionate to the roadmap.

### Trade-offs Accepted
- The project has more moving parts than earlier apps.
- Some CLI code is procedural and could eventually be decomposed further.
- The expanded feature set increases documentation and testing burden.

### Consequences
- The Constitution evaluation should judge App 36 under the medium-project allowance.
- The app is strong evidence of progression in architecture and algorithms.
- Future work should focus on polish, performance limits, and clearer separation of CLI runtime helpers rather than adding unrelated features.

### Superseded By
None.

---

## Constitution Reference

This ADR set supports the Constitution by documenting intentional decisions, not just final code. The project demonstrates Python fundamentals through dataclasses, enums, protocols, pure functions, argparse, JSON, and tests; demonstrates architecture through boundaries between models, engine, agents, CLI, persistence, and renderers; and accepts scope as a medium roadmap project rather than pretending it is a small script.

---

# Technical Design Document

## App 36 — Tic Tac Toe
**Game Systems Group | Document 2 of 5**

---

## 1. Purpose & Scope

Tic Tac Toe is an immutable, testable terminal game package. It supports:

- Classic 3x3 Tic-Tac-Toe.
- Generalized `NxN` boards.
- Configurable `k` marks in a row to win.
- Misère mode, where making the line loses.
- Human, random, heuristic, minimax, and Monte Carlo rollout agents.
- Interactive play, AI watch mode, tournament mode, replay, analysis, and stats.
- JSON saves and persistent aggregate stats.
- Multiple terminal renderers.

The project is intentionally a terminal CLI package, not a GUI game, web service, or multiplayer networked system. It uses the Python standard library at runtime.

---

## 2. System Context

The package is installed as `tictactoe-princ` and exposes the console script:

```text
tictactoe = tictactoe.cli:main
```

At runtime it interacts with:

- The terminal for input and output.
- The user home directory for configuration, saves, stats, and history.
- The Python standard library for argparse, dataclasses, JSON, random, pathlib, enum, and timing.
- Optional dev tooling only for tests, linting, and type checking.

The default application directory is:

```text
~/.tictactoe
```

Important files are:

```text
~/.tictactoe/config.toml
~/.tictactoe/saves/*.json
~/.tictactoe/stats.json
~/.tictactoe/history.jsonl
```

---

## 3. Component Breakdown

### `tictactoe.models`
Owns immutable domain objects and enums.

Primary responsibilities:
- Define `Player`, `Cell`, and `Outcome`.
- Define `Position`, `WinCondition`, `Move`, `Board`, and `GameState`.
- Validate board sizes, win lengths, positions, and cell placement.
- Format boards in compact, numbered, and grid forms.

Important objects:
- `Player.X`, `Player.O`, `Player.NONE`
- `Outcome.IN_PROGRESS`, `X_WINS`, `O_WINS`, `DRAW`, `ABANDONED`
- `Board(size, k, cells)`
- `GameState(board, next_player, history, outcome, winning_line, misere, started_at)`

### `tictactoe.engine`
Owns pure game rules.

Primary responsibilities:
- Produce legal moves.
- Generate all k-length candidate winning lines.
- Check wins/draws.
- Apply moves immutably.
- Abandon games.
- Replay histories.
- Undo plies by replaying a shorter history.

Important functions:
- `available_moves(board)`
- `all_line_positions(size, k)`
- `check_winner(board, misere=False)`
- `make_move(state, position)`
- `abandon(state)`
- `replay(history, size, k, misere, started_at)`
- `undo(state, plies=1)`

### `tictactoe.agents`
Owns human and AI strategy implementations.

Primary responsibilities:
- Parse human position input.
- Choose legal moves for each agent type.
- Implement heuristic, minimax, and Monte Carlo rollout strategies.
- Provide `create_agent()` factory for CLI names.

Important objects:
- `Agent` protocol.
- `HumanAgent`
- `RandomAgent`
- `HeuristicAgent`
- `MinimaxAgent`
- `MonteCarloRolloutAgent`
- `SearchStats`

### `tictactoe.renderers`
Owns state-to-string presentation.

Primary responsibilities:
- Render game state without performing I/O.
- Provide classic, coordinate, minimal, and big views.
- Format outcome text and recent history.
- Apply ANSI styles through a small helper.

Important classes:
- `ClassicRenderer`
- `CoordinateRenderer`
- `MinimalRenderer`
- `BigRenderer`
- `ColorScheme`
- `create_renderer()`

### `tictactoe.display`
Owns terminal output side effects.

Primary responsibilities:
- Call a renderer.
- Avoid redundant redraws.
- Optionally clear the terminal before frames.
- Print frames to stdout.

### `tictactoe.persistence`
Owns JSON serialization and durable state.

Primary responsibilities:
- Convert `GameState` to/from dictionaries.
- Save/load/list/delete JSON game files.
- Provide in-memory repository for tests.
- Store aggregate stats and append per-game history.

Important classes:
- `JsonGameRepository`
- `InMemoryGameRepository`
- `StatsRepository`

### `tictactoe.config`
Owns configuration defaults and TOML loading.

Primary responsibilities:
- Define built-in defaults.
- Load optional `~/.tictactoe/config.toml`.
- Deep-merge user config into defaults.

### `tictactoe.cli`
Owns argparse, command dispatch, and game orchestration.

Primary responsibilities:
- Parse CLI commands and flags.
- Create game options, agents, renderers, repositories, and displays.
- Run interactive games.
- Run AI watch games.
- Run tournaments.
- Replay and analyze saved games.
- Print stats.

### `tictactoe.ansi`
Owns small ANSI escape helpers.

Primary responsibilities:
- Respect `NO_COLOR`.
- Apply style codes.
- Clear terminal or move cursor when needed.

### `tictactoe.exceptions`
Owns domain-specific exception hierarchy.

Primary responsibilities:
- Provide precise exceptions for invalid moves, occupied cells, out-of-bounds positions, game-over moves, and invalid board sizes.

---

## 4. Module Dependency Graph

High-level dependency flow:

```text
__main__
  -> cli

cli
  -> agents
  -> config
  -> display
  -> engine
  -> exceptions
  -> models
  -> persistence
  -> renderers

display
  -> ansi
  -> models
  -> renderers

renderers
  -> ansi
  -> models

agents
  -> engine
  -> exceptions
  -> models

engine
  -> exceptions
  -> models

persistence
  -> config
  -> models

config
  -> pathlib / tomllib

models
  -> exceptions

exceptions
  -> no project imports
```

The intended direction is from outer layers toward inner layers:

```text
CLI / Display / Persistence
        |
Agents / Renderers
        |
Engine
        |
Models / Exceptions
```

The engine does not import CLI, display, persistence, or config. This is the most important dependency boundary.

---

## 5. Core Algorithms & Logic

### 5.1 Move Application

`make_move(state, position)` follows this sequence:

1. Reject the move if the game is already terminal.
2. Reject the position if it is outside the board.
3. Ask the board to place the current player at the position.
4. `Board.place()` rejects `Player.NONE` and occupied cells.
5. `Board.place()` returns a new `Board`.
6. Create a new `Move` with player, position, timestamp, and move number.
7. Call `check_winner()` on the new board.
8. If the game continues, switch `next_player`.
9. Return a new `GameState` with updated board, history, outcome, and winning line.

No mutation occurs in this path.

### 5.2 Win Detection

`all_line_positions(size, k)` generates all contiguous k-position lines in four directions:

```text
(0, 1)   horizontal
(1, 0)   vertical
(1, 1)   diagonal down-right
(1, -1)  diagonal down-left
```

For each board coordinate, the function checks whether a k-length segment in each direction remains inside the board. If yes, it stores the tuple of `Position` objects.

`check_winner(board, misere=False)` then:

1. Iterates through all cached line positions.
2. Reads marks from the board for each line.
3. Checks whether every mark in the line is the same non-empty player.
4. In normal mode, the line maker wins.
5. In misère mode, the line maker's opponent wins.
6. If no line exists and the board is full, returns draw.
7. Otherwise returns in-progress.

### 5.3 Undo

`undo(state, plies)` avoids mutating history or reversing board cells in place.

Sequence:

1. If `plies <= 0`, return the original state.
2. Keep a prefix of `state.history`.
3. Rebuild from a new empty board using `replay()`.
4. Preserve board size, `k`, misère flag, and start timestamp.

This is simpler and safer than trying to remove pieces from an existing board.

### 5.4 Replay

`replay(history, size, k, misere, started_at)` starts with a fresh `GameState` and applies recorded moves through `_apply_recorded_move()`.

`_apply_recorded_move()` validates:
- the recorded player matches the expected `next_player`;
- the state is not already terminal;
- the destination cell is legal.

Replay is therefore a verification step, not just a blind JSON load.

### 5.5 Position Parsing

`parse_position(text, size)` supports several user formats:

```text
A1
1A
row,col
1..N^2 keypad-style numbers
```

For numeric keypad notation, number `1` maps to the lower-left cell on a 3x3-style keypad layout. This is user-friendly but must be documented because it differs from row-major indexing.

### 5.6 Heuristic Agent

The heuristic agent uses a deterministic priority structure with random choice only when multiple equivalent corners or fallback moves exist:

1. Win immediately if a legal move wins.
2. Block the opponent's immediate win.
3. Take center on odd-sized boards.
4. Take an available corner.
5. Pick any legal move.

The agent is fast and readable but not optimal.

### 5.7 Minimax Agent

`MinimaxAgent.choose_move()`:

1. Enumerates legal moves.
2. Optionally makes a random mistake for easy mode.
3. Sets target player to `state.next_player`.
4. Determines max depth:
   - full remaining depth if `depth is None`;
   - otherwise bounded by remaining legal moves.
5. For each root move, evaluates the child board through `_search()`.
6. Tracks the best score and all equally best moves.
7. Returns a random choice among tied best moves.
8. Stores `SearchStats`.

`_search()`:

1. Uses `(board, next_player, depth, target, misere)` as cache key.
2. Checks terminal outcome.
3. Returns depth-adjusted terminal score:
   - target win: positive;
   - target loss: negative;
   - draw: zero.
4. At depth zero, computes a heuristic score over open lines.
5. Otherwise recursively searches child moves.
6. Uses alpha-beta cutoffs to skip branches that cannot change the decision.
7. Caches fully evaluated non-cutoff nodes.

### 5.8 Monte Carlo Rollout Agent

`MonteCarloRolloutAgent` is a flat rollout strategy, not full UCT MCTS.

For each legal root move:

1. Run random playouts from that root move.
2. Play random legal moves until terminal.
3. Score win as `1.0`, draw as `0.5`, loss as `0.0`.
4. Sum average outcomes per root move.
5. Return a random move among best-scoring roots.

This is intentionally simpler than a full tree-structured Monte Carlo search.

### 5.9 Tournament Mode

`tournament` runs many AI-vs-AI games without display. It:

1. Rejects human agents.
2. Creates agents for each game, offsetting seeds to avoid identical games.
3. Auto-plays until terminal state.
4. Counts outcomes.
5. Tracks total moves.
6. Prints aggregate summary.

Tournament mode is for comparison, not persistent save generation.

### 5.10 Replay Command

`replay` loads a saved state, then reconstructs a fresh game by applying saved moves one by one. It can either pause between moves or print all frames with `--no-pause`.

### 5.11 Analysis Command

`analyze` loads a saved game and walks through the move history. At each state it asks `MinimaxAgent` for a recommendation and compares the recorded move to the recommended move, printing `OK` or `DIFF`.

---

## 6. Data Structures

### `Player`
Enum values:

```text
X
O
NONE
```

Important properties:
- `opponent`
- `is_mark`
- `from_value()`

### `Outcome`
Enum values:

```text
in_progress
x_wins
o_wins
draw
abandoned
```

Important properties:
- `winner`
- `is_terminal`
- `for_winner(player)`

### `Position`

```python
@dataclass(frozen=True, order=True)
class Position:
    row: int
    col: int
```

Rows and columns are zero-based internally. User-facing labels are `A1`, `A2`, etc.

### `Board`

```python
@dataclass(frozen=True)
class Board:
    size: int = 3
    k: int = 3
    cells: tuple[Cell, ...] = ()
```

Important invariants:
- `size >= 3`
- `2 <= k <= size`
- `len(cells) == size * size`
- every cell normalizes to `Player`

### `Move`

```python
@dataclass(frozen=True)
class Move:
    player: Player
    position: Position
    timestamp: float
    move_number: int
```

`timestamp` uses monotonic time at move creation. It is useful for ordering and diagnostics, not a wall-clock time.

### `WinCondition`

```python
@dataclass(frozen=True)
class WinCondition:
    player: Player
    positions: tuple[Position, ...]
```

In misère mode, `winning_line.player` identifies the line maker, which is the losing player.

### `GameState`

```python
@dataclass(frozen=True)
class GameState:
    board: Board
    next_player: Player
    history: tuple[Move, ...]
    outcome: Outcome
    winning_line: WinCondition | None
    misere: bool
    started_at: float
```

`GameState` is the single source of truth for engine, agents, renderers, persistence, replay, and analysis.

### Saved Game JSON

A saved game includes:

```json
{
  "version": 1,
  "metadata": {},
  "board": {
    "size": 3,
    "k": 3,
    "cells": ["X", ".", ".", "..."]
  },
  "next_player": "O",
  "history": [
    {
      "player": "X",
      "row": 1,
      "col": 1,
      "timestamp": 123.456,
      "move_number": 1
    }
  ],
  "outcome": "in_progress",
  "winning_line": null,
  "misere": false,
  "started_at": 123.000
}
```

### Stats JSON

`StatsRepository` stores aggregate counts per agent:

```json
{
  "minimax": {"wins": 10, "losses": 0, "draws": 5},
  "random": {"wins": 0, "losses": 10, "draws": 5}
}
```

### History JSONL

Each completed game event includes:

```json
{"completed_at":"2026-05-09T12:00:00","x_agent":"minimax","o_agent":"random","outcome":"x_wins","size":3,"k":3,"moves":7}
```

---

## 7. State Management

### In-Memory State
Game state is immutable and passed explicitly between functions. The current state variable is replaced after each move.

### File-Based State
Persistent state lives under `~/.tictactoe`:
- config TOML;
- JSON saves;
- stats JSON;
- history JSONL.

### Random State
Agents that need randomness accept a `random.Random` instance. CLI-created agents can receive deterministic seeds.

### Terminal State
`Display` optionally clears the terminal but does not manage raw terminal mode. Human input uses normal `input()` prompts.

### Global / Cached State
`all_line_positions()` uses `functools.cache` for line-position generation by `(size, k)`. This is acceptable because the function is pure and the result is immutable.

---

## 8. Error Handling Strategy

### Domain Errors
Custom exceptions include:
- `GameError`
- `InvalidMoveError`
- `CellOccupiedError`
- `OutOfBoundsError`
- `GameOverError`
- `InvalidBoardSizeError`

### CLI Error Handling
`main()` catches:
- `KeyboardInterrupt` and returns `130`;
- `GameError`, `ValueError`, and `FileNotFoundError`, printing `error: ...` and returning `2`.

Argparse errors also return `2` through argparse's standard behavior.

### Human Move Errors
In interactive play, invalid move text or illegal moves are caught inside `_human_turn()`. The error is printed and the same state is redrawn. The process does not exit.

### Save/Load Errors
Loading missing or invalid paths can raise `FileNotFoundError` or `ValueError`, which the CLI converts to exit code `2`.

### Tournament Errors
Invalid tournament settings, such as `--games 0` or human agents, raise `ValueError` and return exit code `2`.

---

## 9. External Dependencies

### Runtime
No third-party runtime dependencies.

### Development
The optional dev dependencies are:
- `pytest`
- `hypothesis`
- `ruff`
- `mypy`

### Python Version
Requires Python `>=3.11`.

---

## 10. Concurrency Model

The application is synchronous.

There are no threads, async tasks, subprocess managers, or event loops in the runtime. Human play blocks on `input()`. Watch mode sleeps between AI moves using `time.sleep(delay)`. Tournament mode runs games sequentially.

This is appropriate for the project scope because all operations are CPU-bound and terminal-based. The main concurrency-related limitation is that long AI searches can block the CLI.

---

## 11. Known Limitations

1. **Minimax scalability.**  
   Full minimax is practical on 3x3 but grows quickly on larger boards.

2. **Monte Carlo is not full MCTS.**  
   The CLI name `mcts` maps to flat rollout Monte Carlo, not UCT.

3. **No save schema migration.**  
   Saves include `version: 1`, but there is no migration layer yet.

4. **No file locking.**  
   Concurrent writes to stats or history are not protected.

5. **`input_mode` is under-realized.**  
   The config and CLI expose `keypad` vs `arrow`, but the visible human-turn implementation uses text input parsing rather than an arrow-key interface.

6. **No GUI or network play.**  
   This is intentional scope discipline.

7. **Tournaments are not persisted as detailed reports.**  
   Tournament results print to stdout but do not save every game.

8. **Move timestamps use monotonic time.**  
   This is good for relative timing but not a human-readable wall-clock record.

---

## 12. Design Patterns Used

### Value Object
`Position`, `Move`, `Board`, `WinCondition`, and `GameState` are value-like immutable objects.

### Pure Function Core
The engine uses pure functions for rules and transitions.

### Strategy
Agents and renderers are strategy families selected by name.

### Factory
`create_agent()` and `create_renderer()` construct concrete implementations from CLI/config names.

### Repository
`JsonGameRepository`, `InMemoryGameRepository`, and `StatsRepository` isolate persistence.

### Command Dispatch
Argparse subcommands dispatch to `cmd_play`, `cmd_watch`, `cmd_tournament`, `cmd_replay`, `cmd_stats`, and `cmd_analyze`.

### Memoization
Minimax uses a local cache; line generation uses `functools.cache`.

---

## 13. Constitution Reference

The technical design satisfies Article 1 through appropriate decomposition and algorithmic design, Article 4 through separation of concerns and custom errors, Article 6 through direct unit tests and CLI tests, and Article 7 through clear progression into game state, AI, persistence, and analysis. Scope is larger than a 24-hour micro app, but it is justified under the medium-project classification.

---

# Interface Design Specification

## App 36 — Tic Tac Toe
**Game Systems Group | Document 3 of 5**

---

## 1. Invocation Syntax

### Installed Console Script

```powershell
tictactoe [COMMAND] [OPTIONS]
```

### Module Form Without Console Script

```powershell
python -m tictactoe [COMMAND] [OPTIONS]
```

### Default Command

If no command is supplied, the CLI defaults to:

```powershell
tictactoe play
```

---

## 2. Command Summary

```text
play        start an interactive game
watch       watch two agents play
tournament  run many games between two agents
replay      step through a saved game
analyze     compare each saved move to minimax
stats       show aggregate agent stats
```

---

## 3. Shared Game Options

These options apply to `play`, `watch`, and `tournament`.

| Name | Type | Required | Default | Valid Values | Description |
|---|---:|---:|---|---|---|
| `--x` | choice | no | config or command default | `human`, `random`, `heuristic`, `minimax`, `minimax-easy`, `minimax-medium`, `minimax-hard`, `mcts` | Agent for X. |
| `--o` | choice | no | config or command default | same as `--x` | Agent for O. |
| `--size` | int | no | config/default `3` | `>= 3` | Board width and height. |
| `--k` | int | no | config/default `3` | `2..size` | Marks in a row needed to win. |
| `--misere` | bool flag | no | config/default `false` | present/absent | Invert line result so line maker loses. |
| `--renderer` | choice | no | config/default `classic` | `classic`, `coordinate`, `minimal`, `big` | Board renderer. |
| `--colors` | choice | no | config/default `classic` | `classic`, `monochrome`, `colorblind` | ANSI color scheme. |
| `--no-color` | bool flag | no | config/default `false` | present/absent | Disable ANSI styling. |
| `--input-mode` | choice | no | config/default `keypad` | `keypad`, `arrow` | Declared input mode. Current human input is text command based. |
| `--seed` | int | no | `None` | any int | Seed for random-capable agents. |
| `--minimax-depth` | int | no | config/default `None`; auto `4` on larger boards when unset | `>= 0` intended | Depth limit for minimax. |
| `--mcts-simulations` | int | no | config/default `200` | positive int intended | Number of rollout simulations for Monte Carlo agent. |

---

## 4. `play` Command

### Syntax

```powershell
tictactoe play [GAME_OPTIONS] [--clear]
```

### Additional Arguments

| Name | Type | Required | Default | Valid Values | Description |
|---|---:|---:|---|---|---|
| `--clear` | bool flag | no | `false` | present/absent | Clear the terminal between frames. |

### Behavior
Starts an interactive game. Defaults normally come from config, with built-in defaults of human X vs minimax O.

### In-Game Input Contract

Human move commands include:

| Input | Meaning |
|---|---|
| `A1` | Row letter + column number. |
| `1A` | Column number + row letter. |
| `row,col` | 1-based row and column numbers. |
| `1`..`9` on 3x3 | Keypad-style numeric position. |
| `hint` | Ask minimax for a recommended move. |
| `u` or `undo` | Undo two plies, or one if only one move exists. |
| `r` or `restart` | Restart current match. |
| `s` or `save` | Save current game. |
| `l` or `load` | Load a saved game. |
| `h`, `?`, or `help` | Print help. |
| `q`, `quit`, or `exit` | Quit and optionally save. |

---

## 5. `watch` Command

### Syntax

```powershell
tictactoe watch [GAME_OPTIONS] [--delay SECONDS] [--clear]
```

### Additional Arguments

| Name | Type | Required | Default | Valid Values | Description |
|---|---:|---:|---|---|---|
| `--delay` | float | no | `0.5` | `>= 0.0` | Delay between AI moves. |
| `--clear` | bool flag | no | `false` | present/absent | Clear terminal between frames. |

### Behavior
Runs an AI-vs-AI game with display. Human agents are rejected.

---

## 6. `tournament` Command

### Syntax

```powershell
tictactoe tournament [GAME_OPTIONS] [--games N]
```

### Additional Arguments

| Name | Type | Required | Default | Valid Values | Description |
|---|---:|---:|---|---|---|
| `--games` | int | no | `100` | `>= 1` | Number of games to run. |

### Behavior
Runs many AI-vs-AI games without rendering every move. Human agents are rejected. Prints outcome counts and average moves.

### Output Contract

Example shape:

```text
Tournament: minimax (X) vs random (O)
Games: 100
x_wins: 73
o_wins: 0
draw: 27
abandoned: 0
Average moves: 7.82
```

---

## 7. `replay` Command

### Syntax

```powershell
tictactoe replay SAVE_FILE [--renderer NAME] [--colors NAME] [--no-color] [--no-pause]
```

### Arguments

| Name | Type | Required | Default | Valid Values | Description |
|---|---:|---:|---|---|---|
| `save_file` | path/name | yes | none | path or save name | Save to replay. |
| `--renderer` | choice | no | config renderer | `classic`, `coordinate`, `minimal`, `big` | Renderer for replay frames. |
| `--colors` | choice | no | config colors | `classic`, `monochrome`, `colorblind` | Color scheme. |
| `--no-color` | bool flag | no | config no_color | present/absent | Disable color. |
| `--no-pause` | bool flag | no | `false` | present/absent | Print all frames without waiting for Enter. |

### Behavior
Loads a saved game, starts from a fresh board, and applies saved moves sequentially. By default it pauses between moves.

---

## 8. `analyze` Command

### Syntax

```powershell
tictactoe analyze SAVE_FILE [--depth N]
```

### Arguments

| Name | Type | Required | Default | Valid Values | Description |
|---|---:|---:|---|---|---|
| `save_file` | path/name | yes | none | path or save name | Save file to analyze. |
| `--depth` | int | no | `None` | `>= 0` intended | Optional minimax depth limit. |

### Behavior
For each saved move, minimax recommends a move from the current state. The command prints whether the recorded move matches the minimax recommendation.

### Output Contract

Example shape:

```text
Analyzing 5 moves with minimax
01. X@A1 best=B2 DIFF
02. O@B2 best=B2 OK
...
X wins. Moves: 5.
```

---

## 9. `stats` Command

### Syntax

```powershell
tictactoe stats
```

### Behavior
Reads aggregate stats from `~/.tictactoe/stats.json`.

If no stats exist:

```text
No completed games recorded yet.
```

If stats exist:

```text
Agent stats
heuristic        wins=   3 losses=   5 draws=   2
minimax          wins=   8 losses=   0 draws=   2
```

---

## 10. Input Contract

### Board Size
- `size` must be at least `3`.
- Board cells are a flat tuple internally with `size * size` cells.

### Win Length
- `k` must be at least `2`.
- `k` must be less than or equal to `size`.

### Position Input
Accepted coordinate formats:
- row-letter then column: `A1`;
- column then row-letter: `1A`;
- comma position: `1,1`;
- keypad number: `1` through `size * size`.

Invalid input raises or prints an invalid move message depending on context.

### Save File Input
`replay` and `analyze` accept:
- full paths;
- save names under `~/.tictactoe/saves`;
- names with or without `.json`.

---

## 11. Output Contract

### Human-Oriented Output
Most commands print readable terminal text. Renderers may include ANSI color unless disabled.

### Minimal Renderer Output
The minimal renderer returns:

```text
BOARD_COMPACT OUTCOME
```

Example:

```text
X..|.O.|... in_progress
```

### JSON Save Output
Interactive save prints:

```text
Saved /home/user/.tictactoe/saves/name.json
```

The save file itself is JSON with version, board, history, outcome, winning line, misère flag, and timestamp fields.

---

## 12. Exit Code Reference

| Exit Code | Condition |
|---:|---|
| `0` | Successful command completion. |
| `2` | CLI argument error from argparse, invalid board/agent/renderer/config, missing save file, game domain error, or other caught value/file error. |
| `130` | Keyboard interrupt. |

---

## 13. Error Output Behavior

`main()` prints caught command errors to stderr in this form:

```text
error: <message>
```

Argparse prints its own usage and error text to stderr.

Interactive human move errors are printed to stdout and the game continues.

---

## 14. Environment Variables

| Variable | Effect |
|---|---|
| `NO_COLOR` | Disables ANSI color styling when present. |
| `PYTHONPATH` | Can be set to `src` for running without installation. |

No project-specific environment variables are required.

---

## 15. Configuration Files

### Path

```text
~/.tictactoe/config.toml
```

### Example

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

### Precedence
1. CLI flags.
2. Config file.
3. Built-in defaults.

---

## 16. Side Effects

| Command | Side Effects |
|---|---|
| `play` | May save games; records completed game stats/history. |
| `watch` | Records completed game stats/history. |
| `tournament` | Prints aggregate results; does not save every game. |
| `replay` | Reads save files; no write expected. |
| `analyze` | Reads save files; no write expected. |
| `stats` | Reads `stats.json`. |
| In-game `s` | Writes a save file. |
| In-game `q` with save prompt accepted | Writes a save file before abandoning. |

---

## 17. Usage Examples

### Basic interactive game

```powershell
tictactoe play
```

### Human vs minimax with coordinate renderer

```powershell
tictactoe play --x human --o minimax --renderer coordinate
```

### Generalized 4x4 board with 3 in a row

```powershell
tictactoe play --x human --o minimax-medium --size 4 --k 3
```

### Misère mode

```powershell
tictactoe play --x human --o heuristic --misere
```

### Watch AI agents

```powershell
tictactoe watch --x minimax --o mcts --size 4 --k 3 --delay 0.25
```

### Run a tournament

```powershell
tictactoe tournament --x minimax --o random --games 100 --seed 42
```

### Replay a saved game

```powershell
tictactoe replay center-game.json
```

### Replay without pauses

```powershell
tictactoe replay center-game.json --no-pause --renderer minimal
```

### Analyze a saved game

```powershell
tictactoe analyze center-game.json --depth 4
```

### Show stats

```powershell
tictactoe stats
```

### Intentional failure: invalid tournament human agent

```powershell
tictactoe tournament --x human --o random
```

Expected behavior:

```text
error: tournament does not support human agents
```

Exit code: `2`.

---

## 18. Constitution Reference

The interface is larger than a micro utility but coherent: every command maps to a clear game operation. The app satisfies Article 6 through reproducible command paths and tests, and Article 5 through documented contracts, side effects, and failure modes.

---

# Runbook

## App 36 — Tic Tac Toe
**Game Systems Group | Document 4 of 5**

---

## 1. Prerequisites

- Python 3.11 or newer.
- A terminal capable of standard input/output.
- No runtime third-party packages.
- Optional development tools:
  - pytest
  - hypothesis
  - ruff
  - mypy

Supported practical environments:
- Windows PowerShell.
- macOS terminal.
- Linux shell.
- WSL/Git Bash for Windows-style development flows.

---

## 2. Installation Procedure

### Editable Runtime Install

From the repository root:

```powershell
python -m pip install -e .
```

Verify the command exists:

```powershell
tictactoe --help
```

### Development Install

```powershell
python -m pip install -e ".[dev]"
```

Run checks:

```powershell
python -m pytest
ruff check src tests
mypy src
```

### Run Without Installing

PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m tictactoe --help
```

Unix shell:

```bash
PYTHONPATH=src python -m tictactoe --help
```

---

## 3. Configuration Steps

Configuration is optional. The app works with built-in defaults.

To configure defaults, create:

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

If the file is skipped, built-in defaults are used. CLI flags override config values.

---

## 4. Standard Operating Procedures

### 4.1 Start a Normal Game

```powershell
tictactoe play
```

Expected:
- Board renders.
- Human X is prompted.
- O moves by configured/default agent.

### 4.2 Play Human vs Minimax

```powershell
tictactoe play --x human --o minimax
```

### 4.3 Use Coordinate Renderer

```powershell
tictactoe play --renderer coordinate
```

Use this when teaching coordinates or reducing input mistakes.

### 4.4 Play a Larger Board

```powershell
tictactoe play --size 4 --k 3 --x human --o minimax-medium
```

For larger boards, prefer `minimax-medium`, `heuristic`, `random`, or `mcts` unless you intentionally want a heavy search.

### 4.5 Play Misère Mode

```powershell
tictactoe play --misere --x human --o heuristic
```

In this mode, the player who completes the line loses.

### 4.6 Watch AI Agents

```powershell
tictactoe watch --x minimax --o heuristic --delay 0.5
```

### 4.7 Run Tournament

```powershell
tictactoe tournament --x minimax --o random --games 100 --seed 7
```

Use `--seed` when comparing results across repeated runs.

### 4.8 Save During Interactive Play

During `play`, enter:

```text
s
```

Then supply a save name. The file is written under:

```text
~/.tictactoe/saves
```

### 4.9 Load During Interactive Play

During `play`, enter:

```text
l
```

Then choose a listed save or enter a path.

### 4.10 Replay Save

```powershell
tictactoe replay center-game.json
```

For non-interactive output:

```powershell
tictactoe replay center-game.json --no-pause
```

### 4.11 Analyze Save

```powershell
tictactoe analyze center-game.json
```

Use a depth limit for larger boards:

```powershell
tictactoe analyze big-game.json --depth 4
```

### 4.12 Show Stats

```powershell
tictactoe stats
```

---

## 5. Health Checks

### Check CLI Availability

```powershell
tictactoe --help
```

Success means the package is installed and the console script resolves.

### Check Module Entry Point

```powershell
python -m tictactoe --help
```

Success means module execution works.

### Check Standard Game Path

```powershell
tictactoe tournament --x minimax --o random --games 1 --seed 1
```

Expected:
- exit code `0`;
- tournament summary printed;
- no human input required.

### Check Save/Replay Path

1. Start a game:

```powershell
tictactoe play
```

2. Make a move.
3. Type `s`.
4. Save as `health-check`.
5. Exit.
6. Replay:

```powershell
tictactoe replay health-check --no-pause
```

### Check Tests

```powershell
python -m pytest
```

The README indicates pytest is the main test runner, with unittest discovery also supported from the repo root.

---

## 6. Expected Output Samples

### Tournament

```text
Tournament: minimax (X) vs random (O)
Games: 2
x_wins: 2
o_wins: 0
draw: 0
abandoned: 0
Average moves: 6.50
```

### Stats When Empty

```text
No completed games recorded yet.
```

### Analysis

```text
Analyzing 5 moves with minimax
01. X@A1 best=B2 DIFF
02. O@B2 best=B2 OK
X wins. Moves: 5.
```

### Minimal Renderer

```text
X..|.O.|... in_progress
```

---

## 7. Known Failure Modes

| Failure Mode | Trigger | Output / Symptom | Resolution |
|---|---|---|---|
| Invalid board size | `--size 2` | `error: Board size must be at least 3` | Use size 3 or larger. |
| Invalid k | `--size 3 --k 4` | `error: Win length k must be between 2 and board size` | Use `2 <= k <= size`. |
| Human in tournament | `tournament --x human` | `error: tournament does not support human agents` | Use AI agents only. |
| Human in watch | `watch --x human` | `error: watch requires AI agents` | Use `play` for human games. |
| Missing save | `replay missing` | `error: missing` or file-not-found message | Check save name/path under `~/.tictactoe/saves`. |
| Occupied cell | Human repeats a move | Message printed and prompt repeats | Choose an open cell. |
| AI search slow | large board + full minimax | long pause | Use `--minimax-depth`, heuristic, or mcts. |
| Color unwanted | ANSI escape codes visible | colored/control text | Use `--no-color` or set `NO_COLOR=1`. |
| Config typo | invalid values in TOML | error during command | Fix or temporarily move config file. |
| Stats missing | first `stats` run | `No completed games recorded yet.` | Complete a play/watch game first. |

---

## 8. Troubleshooting Decision Tree

### Symptom: `tictactoe` command not found
Probable cause: package not installed in the active environment.

Diagnostic:

```powershell
python -m pip show tictactoe-princ
```

Resolution:

```powershell
python -m pip install -e .
```

Alternative:

```powershell
$env:PYTHONPATH = "src"
python -m tictactoe --help
```

### Symptom: import error when running tests
Probable cause: `src` not on import path or package not installed.

Diagnostic:

```powershell
python -m pytest
```

Resolution:

```powershell
python -m pip install -e ".[dev]"
```

### Symptom: tournament is very slow
Probable cause: expensive AI combination or large board.

Diagnostic:
Check command for `--size`, `--k`, and minimax depth.

Resolution:
Use one of:

```powershell
--minimax-depth 4
--x heuristic --o random
--x mcts --o heuristic
```

### Symptom: replay fails to find save
Probable cause: save is not in `~/.tictactoe/saves`, wrong extension, or wrong path.

Diagnostic:
List saves:

```powershell
dir ~/.tictactoe/saves
```

Resolution:
Use the exact file path or save name.

### Symptom: color appears wrong
Probable cause: terminal does not support ANSI or color is undesired.

Resolution:

```powershell
tictactoe play --no-color
```

or set:

```powershell
$env:NO_COLOR = "1"
```

### Symptom: invalid move accepted in input prompt but not applied
Probable cause: coordinate parsing format was wrong.

Resolution:
Use clear coordinate format:

```text
A1
1A
1,1
```

Remember `row,col` is 1-based; internal positions are zero-based.

---

## 9. Dependency Failure Handling

### Runtime Dependencies
There are no third-party runtime dependencies. Most dependency failures are Python environment or package installation issues.

### Dev Dependencies
If pytest, Hypothesis, Ruff, or Mypy are missing:

```powershell
python -m pip install -e ".[dev]"
```

### TOML Support
Python 3.11 includes `tomllib`. If using an older Python version, upgrade to Python 3.11+ rather than adding a dependency.

---

## 10. Recovery Procedures

### Recover from Bad Config
Move the config file aside:

```powershell
move ~/.tictactoe/config.toml ~/.tictactoe/config.toml.bak
```

Run with defaults:

```powershell
tictactoe --help
```

### Recover from Corrupted Save
A corrupted save may fail to load. Options:

1. Open the JSON file and validate required fields.
2. Restore from another save.
3. Delete the corrupted file if not needed.

Saves are under:

```text
~/.tictactoe/saves
```

### Reset Stats
Delete or rename:

```text
~/.tictactoe/stats.json
~/.tictactoe/history.jsonl
```

### Avoid Slow AI Runs
Use:

```powershell
tictactoe play --size 4 --k 3 --o minimax-medium
```

or:

```powershell
tictactoe play --o heuristic
```

### Abort a Running Command
Press `Ctrl+C`.

Expected exit code: `130`.

---

## 11. Logging Reference

The app does not use a logging framework for normal operation.

Persistent operational records are:
- aggregate stats: `~/.tictactoe/stats.json`;
- append-only game history: `~/.tictactoe/history.jsonl`;
- saved games: `~/.tictactoe/saves/*.json`.

For debugging, use:
- minimal renderer;
- seeded tournament runs;
- saved games plus `replay`;
- saved games plus `analyze`.

---

## 12. Maintenance Notes

1. **AI performance must be watched.**  
   Any new board-size defaults should consider minimax cost.

2. **Save schema should be versioned deliberately.**  
   `version: 1` exists, but migration is not implemented.

3. **Input mode should be clarified.**  
   The CLI/config mention `arrow`, but the current human path is text input. Either implement arrow-key controls or remove the exposed option.

4. **Tournament persistence could be expanded.**  
   Current tournament summaries print to stdout. A future tournament report file would improve repeatability.

5. **Stats/history files may grow.**  
   Add rotation or pruning if the app is used heavily.

6. **MCTS naming should remain documented.**  
   The code correctly notes it is flat rollout Monte Carlo, not full UCT.

7. **Renderer tests should remain pure.**  
   Keep renderers state-to-string and leave stdout to `Display`.

---

## 13. Constitution Reference

The runbook provides behavior verification paths and recovery procedures under Constitution Article 6. It also documents scope and operational side effects, satisfying Article 5. The app is acceptable as a medium project because the extra features are cohesive around a game-system architecture.

---

# Lessons Learned

## App 36 — Tic Tac Toe
**Game Systems Group | Document 5 of 5**

---

## 1. Project Summary

Tic Tac Toe is a terminal game package built around immutable game state. It supports classic and generalized boards, configurable win length, misère mode, multiple agents, minimax search, flat Monte Carlo rollout, JSON saves, replay, analysis, tournament mode, renderers, and persistent stats. The project achieved more than a simple playable game: it became a small game-system architecture where the same pure engine supports human play, AI search, replay, and verification.

---

## 2. Original Goals vs. Actual Outcome

### Original Goals
- Build a playable Tic-Tac-Toe CLI.
- Support human and AI play.
- Keep the rules testable.
- Save and replay games.
- Demonstrate architectural growth.

### Actual Outcome
The delivered app met and exceeded those goals. It includes immutable domain models, generalized board dimensions, a configurable `k` win condition, misère rules, multiple agents, tournament mode, post-game minimax analysis, JSON persistence, stats, and several renderers.

### Gaps
The main gap is not rule correctness but polish around some advanced interface claims. The `input_mode` configuration exposes `keypad` and `arrow`, but the current human turn implementation is command-text based. Also, the CLI name `mcts` is convenient but should always be described as flat Monte Carlo rollout rather than full MCTS.

---

## 3. Technical Decisions That Paid Off

### Immutable State
This was the most important decision. It made undo, replay, AI search, and tests significantly easier. Instead of reversing mutations, the app can rebuild state from history.

### Pure Engine Functions
Keeping `make_move`, `check_winner`, `available_moves`, `undo`, and `replay` free of I/O made the engine reusable by every command and agent.

### Agent Strategy Pattern
The common `choose_move(state)` shape made human and AI players interchangeable. The same game loop can work with human/minimax, minimax/random, mcts/heuristic, or any future agent.

### Generalized Win Detection
Generating k-length lines prevented hard-coded 3x3 assumptions and allowed `4x4, k=3` style games without rewriting rule logic.

### JSON Persistence
JSON saves are easy to inspect and give replay/analysis a concrete artifact to operate on.

### Minimax Stats
`SearchStats` makes the AI less opaque by exposing node visits, cache hits, depth, and elapsed time.

---

## 4. Technical Decisions That Created Debt

### CLI Runtime Is Procedural
`cli.py` coordinates many responsibilities: argument parsing, config merging, agent creation, game loop, human commands, tournament, replay, stats, and analysis. It works, but the file carries more orchestration weight than ideal.

A future refactor could introduce a `GameRunner`, `ReplayRunner`, and `TournamentRunner`.

### Input Mode Flag Is Ahead of Implementation
The config and CLI expose `input_mode`, including `arrow`, but the actual human interaction uses text prompts. This creates interface debt because users may expect arrow-key controls.

### Save Schema Has Version But No Migration
The save payload includes `version: 1`, but there is no migration function. This is fine for a student project, but it should be addressed if saved files are expected to survive future model changes.

### Monte Carlo Agent Name
The CLI uses `mcts`, but the implementation is flat rollout Monte Carlo. The code comments are honest about this, but the CLI name can still mislead unless documentation stays clear.

### Tournaments Do Not Persist Full Reports
Tournament mode prints summaries, but it does not save detailed game histories or final states. This limits deeper analysis of tournament results.

---

## 5. What Was Harder Than Expected

### Generalized Win Detection
Classic 3x3 Tic-Tac-Toe has only eight winning lines. Generalized `NxN, k-in-a-row` boards require scanning many contiguous segments in multiple directions. Getting diagonal boundaries right is more subtle than the classic version.

### Keeping Minimax Practical
Full-depth minimax works for 3x3 but quickly becomes expensive. The project had to introduce depth limits and heuristic leaf scoring for larger boards.

### Human Input Compatibility
Supporting `A1`, `1A`, `row,col`, and keypad-style numbers improves usability, but it also adds parsing edge cases and error handling paths.

### Replay Correctness
Replay should not just display a saved final board. It should rebuild the game from moves and catch impossible histories. That requires careful separation between state serialization and rule-based reconstruction.

### Misère Mode
Misère mode looks like a small boolean, but it changes winner semantics. The line maker and the actual winner can differ, so renderers and outcome text need to explain the result clearly.

---

## 6. What Was Easier Than Expected

### Undo
Because state is immutable and history is explicit, undo became a replay problem. There was no need to mutate cells backward.

### JSON Saves
The model is composed of dataclasses, enums, tuples, and primitives, so converting to/from dictionaries was direct.

### Renderer Extension
Once renderers were pure `render(state) -> str` classes, adding coordinate, minimal, and big views did not require changes to the engine.

### Agent Swapping
The strategy interface made it easy for the CLI to compose different X and O players.

---

## 7. Python-Specific Learnings

### Frozen Dataclasses
`@dataclass(frozen=True)` is a strong fit for game-state modeling. It catches accidental mutation and makes values safer to pass around.

### Enum Semantics
Enums made players and outcomes clearer than raw strings. Properties like `Player.opponent` and `Outcome.winner` concentrated small pieces of logic in the right place.

### Tuple-Based Immutability
Using tuples for cells and history supports hashability and prevents item assignment.

### `functools.cache`
Caching all generated line positions is a simple optimization because line generation depends only on `size` and `k`.

### `argparse` Subcommands
Subcommands made the CLI understandable even with many modes.

### `random.Random`
Injecting seeded random generators makes AI behavior reproducible in tests and tournaments.

### `json` and `pathlib`
The standard library is enough for readable persistence in a project of this size.

---

## 8. Architecture Insights

### The Engine Should Stay Boring
The best part of the architecture is that the engine is small and unsurprising. Most complexity lives at the edges: agents, CLI, persistence, and renderers. That is the right distribution.

### AI Search Rewards Immutability
Minimax is much easier when board states can be safely reused and cached. A mutable board would require careful apply/unapply logic and would be more error-prone.

### Replay Is an Architectural Test
If replay is easy, the engine boundary is probably good. If replay requires terminal, CLI, or hidden state, the design is probably too coupled.

### Medium Scope Needs Hard Boundaries
This app has enough features to sprawl. The reason it remains understandable is that major concepts have module boundaries: models, engine, agents, renderers, persistence, config, display, CLI.

---

## 9. Testing Gaps

### Covered Areas
The available tests cover:
- board immutability;
- row wins;
- generalized 4x4/k=3 wins;
- draws;
- invalid moves;
- undo;
- available moves;
- misère behavior;
- random, heuristic, minimax, human, and Monte Carlo agents;
- minimax not losing to random;
- minimax-vs-minimax drawing;
- tournament CLI summary;
- JSON and in-memory persistence round trips.

### Gaps
- More CLI subprocess tests would strengthen confidence in installed command behavior.
- Renderer tests are not visible in the inspected test set and would be useful for output stability.
- Save/load error cases could be tested more deeply.
- Stats repository behavior could be tested directly.
- Large-board minimax performance boundaries could use explicit tests or benchmarks.
- Replay and analyze command outputs could use integration tests with temporary saves.
- Config loading with nested TOML overrides could use direct tests.
- The exposed `input_mode` option needs either implementation tests or removal.

---

## 10. Reusable Patterns Identified

### Immutable State + Pure Transitions
This pattern applies to many apps beyond games: calculators, simulations, workflows, state machines, and visualizers.

### Strategy Families
Agents and renderers show how to add behavior without modifying core rules.

### Repository Abstraction
A JSON repository plus in-memory repository is a practical pattern for making persistence testable.

### Analysis from Replay
Saved histories can support post-hoc analysis when the engine is deterministic.

### CLI Factory Functions
`create_agent()` and `create_renderer()` are simple but useful factories for turning command-line choices into objects.

### Seeded Randomness
Passing seeds into randomized agents or simulations makes tests and tournaments reproducible.

---

## 11. If I Built This Again

### First Change: Split CLI Orchestration
I would split `cli.py` into smaller modules:

```text
cli.py
game_runner.py
human_commands.py
tournament.py
analysis.py
```

This would preserve behavior while making each runtime path easier to test and modify.

### Second Change: Clarify or Implement Input Modes
I would either implement arrow-key navigation or remove the `arrow` input mode. Exposing an option before supporting it creates avoidable confusion.

### Third Change: Add Save Schema Validation
I would add explicit validation and migration for save files. A version field is useful only if future code knows how to handle older versions.

### Fourth Change: Add Detailed Tournament Reports
I would optionally write tournament runs as JSONL so results can be analyzed later.

---

## 12. Open Questions

1. Should `mcts` be renamed to `rollout` in the CLI, while keeping `mcts` as an alias?
2. Should tournament mode record aggregate stats, detailed game histories, or remain stdout-only?
3. Should move timestamps be wall-clock time, monotonic time, or both?
4. Should human input eventually support true arrow-key selection?
5. Should minimax use a persistent transposition table across games?
6. Should saved games be replayed strictly from history instead of trusting the serialized final board?
7. Should large-board defaults favor Monte Carlo or heuristic agents instead of depth-limited minimax?
8. Should renderer output be snapshot-tested for stability?

---

## 13. Constitution Checklist

### Article 1 — Python Fundamentals and Architecture
Pass. The project uses dataclasses, enums, protocols, pure functions, factories, repositories, argparse, JSON, and tests in a coherent architecture.

### Article 2 — Honest Skill and Authorship
No authorship concern is evident from the inspected files. The project reflects a realistic progression from basic CLI apps toward medium-scale architecture.

### Article 3 — Scope Discipline
Pass as a medium roadmap project. It is larger than a 24-hour micro utility, but the features are cohesive and bounded.

### Article 4 — Engineering Quality
Pass. The project has clear model/engine/agent/renderer/persistence boundaries and custom exception types.

### Article 5 — Trade-Offs and Constraints
Pass. Important trade-offs include minimax scalability, flat Monte Carlo naming, procedural CLI orchestration, and JSON persistence limitations.

### Article 6 — Verification
Pass. The inspected tests cover engine rules, immutability, generalized boards, AI agents, CLI tournament behavior, and persistence.

### Article 7 — Progressive Complexity
Strong pass. This app demonstrates state management, persistence, AI search, replay, analysis, and generalized rules.

### Article 8 — Final Evaluation Standard
Valid learner work. The app is honest, intentional, understandable, verifiable, and reflective. It has improvement areas, but those are proportionate to the medium-project scope and do not undermine the core learning value.
