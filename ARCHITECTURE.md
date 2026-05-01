# Architecture

## 1. Immutable State Is The Core Invariant

`Board`, `GameState`, `Move`, `Position`, and `WinCondition` are frozen dataclasses. Applying a move creates a new `Board` and a new `GameState`; the previous objects remain unchanged.

That one invariant makes undo, replay, testing, and AI search straightforward. A state can be hashed, compared, saved, or passed into a search function without worrying that another part of the program changed it.

## 2. The Engine Is Pure

The rules live in `tictactoe.engine`:

- `make_move(state, position) -> GameState`
- `available_moves(board) -> list[Position]`
- `check_winner(board) -> GameCheck`
- `undo(state, plies=1) -> GameState`
- `replay(history, size, k, misere) -> GameState`

These functions do not read the terminal, write files, or mutate hidden state. Invalid moves raise the custom exception hierarchy from `tictactoe.exceptions`.

## 3. Agents Are A Strategy Family

Agents share the same shape: `choose_move(state: GameState) -> Position`.

The CLI can compose any X agent with any O agent:

- `HumanAgent` (optional `read_line` / `echo` for tests or alternate UIs)
- `RandomAgent`
- `HeuristicAgent`
- `MinimaxAgent`
- `MonteCarloRolloutAgent` (CLI name `mcts`; flat rollout Monte Carlo, not full UCT). Alias `MCTSAgent`.

Because agents only receive immutable state and return positions, human and AI players are interchangeable from the engine's perspective.

## 4. Renderers Are Pure State-To-String Functions

Renderers take a `GameState` and return a string. The terminal-facing `Display` class owns printing and optional screen clearing.

Available renderers:

- `ClassicRenderer`
- `CoordinateRenderer`
- `MinimalRenderer`
- `BigRenderer`

Color is handled by a small ANSI helper that respects `NO_COLOR` and `--no-color`.

## 5. Replay And Analysis Are Consequences

Since history is a tuple of `Move` objects and state transitions are pure, replay is just "start from an empty board and apply these moves again."

The `analyze` command uses the same fact. It walks through a saved history, asks minimax what it would play at each point, and compares that recommendation to the recorded move.

