"""Human and AI agents for the game of Tic-Tac-Toe."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from .engine import GameCheck, all_line_positions, available_moves, check_winner, make_move
from .exceptions import InvalidMoveError, OutOfBoundsError
from .models import Board, GameState, Outcome, Player, Position


@dataclass(frozen=True)
class SearchStats:
    nodes_visited: int = 0
    cache_hits: int = 0
    elapsed_seconds: float = 0.0
    depth: int | None = None

    def __str__(self) -> str:
        depth = "full" if self.depth is None else str(self.depth)
        return (
            f"nodes={self.nodes_visited}, cache_hits={self.cache_hits}, "
            f"depth={depth}, elapsed={self.elapsed_seconds:.3f}s"
        )


class Agent(Protocol):
    name: str
    last_stats: SearchStats | None

    def choose_move(self, state: GameState) -> Position:
        """Choose a legal move for state.next_player."""


def parse_position(text: str, size: int) -> Position:
    token = text.strip().upper().replace(" ", "")
    if not token:
        raise InvalidMoveError("Enter a cell such as A1 or 7")

    if "," in token:
        row_text, col_text = token.split(",", 1)
        row = int(row_text) - 1
        col = int(col_text) - 1
        return _checked_position(row, col, size)

    if token.isdigit():
        value = int(token)
        if value < 1 or value > size * size:
            raise OutOfBoundsError(f"Number must be between 1 and {size * size}")
        zero_based = value - 1
        row_from_bottom = zero_based // size
        col = zero_based % size
        row = size - 1 - row_from_bottom
        return _checked_position(row, col, size)

    if token[0].isalpha() and token[1:].isdigit():
        row = Position.ROW_LABELS.find(token[0])
        col = int(token[1:]) - 1
        if row < 0:
            raise OutOfBoundsError(f"Unknown row label {token[0]!r}")
        return _checked_position(row, col, size)

    if token[-1].isalpha() and token[:-1].isdigit():
        row = Position.ROW_LABELS.find(token[-1])
        col = int(token[:-1]) - 1
        if row < 0:
            raise OutOfBoundsError(f"Unknown row label {token[-1]!r}")
        return _checked_position(row, col, size)

    raise InvalidMoveError("Use A1, 1A, row,col, or keypad number notation")


def _checked_position(row: int, col: int, size: int) -> Position:
    position = Position(row, col)
    position.to_index(size)
    return position


class HumanAgent:
    name = "human"
    last_stats: SearchStats | None = None

    def __init__(
        self,
        *,
        read_line: Callable[[str], str] | None = None,
        echo: Callable[[object], None] | None = None,
    ) -> None:
        self._read_line = read_line if read_line is not None else input
        self._echo = echo if echo is not None else print

    def choose_move(self, state: GameState) -> Position:
        while True:
            try:
                return parse_position(
                    self._read_line(f"{state.next_player.value} move: "),
                    state.board.size,
                )
            except (InvalidMoveError, ValueError) as exc:
                self._echo(exc)


class RandomAgent:
    name = "random"

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.last_stats: SearchStats | None = None

    def choose_move(self, state: GameState) -> Position:
        moves = available_moves(state.board)
        if not moves:
            raise InvalidMoveError("No legal moves are available")
        return self.rng.choice(moves)


class HeuristicAgent:
    name = "heuristic"

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.last_stats: SearchStats | None = None

    def choose_move(self, state: GameState) -> Position:
        moves = available_moves(state.board)
        if not moves:
            raise InvalidMoveError("No legal moves are available")
        player = state.next_player
        opponent = player.opponent

        for move in moves:
            if _simulated_outcome(state.board, player, move, state.misere).outcome.winner is player:
                return move

        for move in moves:
            if _simulated_outcome(state.board, opponent, move, state.misere).outcome.winner is opponent:
                return move

        center = Position(state.board.size // 2, state.board.size // 2)
        if state.board.size % 2 == 1 and center in moves:
            return center

        corners = [
            Position(0, 0),
            Position(0, state.board.size - 1),
            Position(state.board.size - 1, 0),
            Position(state.board.size - 1, state.board.size - 1),
        ]
        open_corners = [corner for corner in corners if corner in moves]
        if open_corners:
            return self.rng.choice(open_corners)

        return self.rng.choice(moves)


def _simulated_outcome(board: Board, player: Player, position: Position, misere: bool) -> GameCheck:
    return check_winner(board.place(player, position), misere=misere)


class MinimaxAgent:
    name = "minimax"

    def __init__(
        self,
        *,
        depth: int | None = None,
        mistake_chance: float = 0.0,
        rng: random.Random | None = None,
    ) -> None:
        self.depth = depth
        self.mistake_chance = mistake_chance
        self.rng = rng or random.Random()
        self.last_stats: SearchStats | None = None

    @classmethod
    def easy(cls, rng: random.Random | None = None) -> MinimaxAgent:
        return cls(depth=None, mistake_chance=0.40, rng=rng)

    @classmethod
    def medium(cls, rng: random.Random | None = None) -> MinimaxAgent:
        return cls(depth=4, rng=rng)

    @classmethod
    def hard(cls, rng: random.Random | None = None) -> MinimaxAgent:
        return cls(depth=None, rng=rng)

    def choose_move(self, state: GameState) -> Position:
        moves = available_moves(state.board)
        if not moves:
            raise InvalidMoveError("No legal moves are available")
        if self.mistake_chance and self.rng.random() < self.mistake_chance:
            self.last_stats = SearchStats(depth=self.depth)
            return self.rng.choice(moves)

        started = monotonic()
        target = state.next_player
        max_depth = len(moves) if self.depth is None else min(self.depth, len(moves))
        counters = {"nodes": 0, "hits": 0}
        cache: dict[tuple[Board, Player, int, Player, bool], int] = {}
        best_score = -10_000
        best_moves: list[Position] = []

        for move in moves:
            child = state.board.place(target, move)
            score = self._search(
                child,
                target.opponent,
                max_depth - 1,
                target,
                state.misere,
                -10_000,
                10_000,
                cache,
                counters,
            )
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        self.last_stats = SearchStats(
            nodes_visited=counters["nodes"],
            cache_hits=counters["hits"],
            elapsed_seconds=monotonic() - started,
            depth=self.depth,
        )
        return self.rng.choice(best_moves)

    def _search(
        self,
        board: Board,
        next_player: Player,
        depth: int,
        target: Player,
        misere: bool,
        alpha: int,
        beta: int,
        cache: dict[tuple[Board, Player, int, Player, bool], int],
        counters: dict[str, int],
    ) -> int:
        key = (board, next_player, depth, target, misere)
        if key in cache:
            counters["hits"] += 1
            return cache[key]

        counters["nodes"] += 1
        check = check_winner(board, misere=misere)
        if check.outcome is not Outcome.IN_PROGRESS:
            value = _terminal_score(check.outcome, target, depth)
            cache[key] = value
            return value
        if depth == 0:
            value = _heuristic_score(board, target, misere)
            cache[key] = value
            return value

        moves = available_moves(board)
        cut_off = False
        if next_player is target:
            value = -10_000
            for move in moves:
                value = max(
                    value,
                    self._search(
                        board.place(next_player, move),
                        next_player.opponent,
                        depth - 1,
                        target,
                        misere,
                        alpha,
                        beta,
                        cache,
                        counters,
                    ),
                )
                alpha = max(alpha, value)
                if alpha >= beta:
                    cut_off = True
                    break
        else:
            value = 10_000
            for move in moves:
                value = min(
                    value,
                    self._search(
                        board.place(next_player, move),
                        next_player.opponent,
                        depth - 1,
                        target,
                        misere,
                        alpha,
                        beta,
                        cache,
                        counters,
                    ),
                )
                beta = min(beta, value)
                if alpha >= beta:
                    cut_off = True
                    break

        if not cut_off:
            cache[key] = value
        return value


def _terminal_score(outcome: Outcome, target: Player, depth: int) -> int:
    if outcome is Outcome.DRAW:
        return 0
    winner = outcome.winner
    if winner is target:
        return 1_000 + depth
    if winner is target.opponent:
        return -1_000 - depth
    return 0


def _heuristic_score(board: Board, target: Player, misere: bool) -> int:
    opponent = target.opponent
    score = 0
    for line in all_line_positions(board.size, board.k):
        marks = [board.at(position) for position in line]
        target_count = marks.count(target)
        opponent_count = marks.count(opponent)
        if target_count and opponent_count:
            continue
        if target_count:
            score += 10**target_count
        if opponent_count:
            score -= 10**opponent_count
    return -score if misere else score


class MonteCarloRolloutAgent:
    """Flat Monte Carlo: rollouts from each candidate root move (not full UCT)."""

    name = "mcts"

    def __init__(self, *, simulations: int = 200, rng: random.Random | None = None) -> None:
        self.simulations = simulations
        self.rng = rng or random.Random()
        self.last_stats: SearchStats | None = None

    def choose_move(self, state: GameState) -> Position:
        moves = available_moves(state.board)
        if not moves:
            raise InvalidMoveError("No legal moves are available")
        started = monotonic()
        player = state.next_player
        scores: dict[Position, float] = dict.fromkeys(moves, 0.0)
        playouts = 0

        for move in moves:
            for _ in range(max(1, self.simulations // len(moves))):
                scores[move] += self._playout_after(state, move, player)
                playouts += 1

        best = max(scores.values())
        best_moves = [move for move, score in scores.items() if score == best]
        self.last_stats = SearchStats(nodes_visited=playouts, elapsed_seconds=monotonic() - started)
        return self.rng.choice(best_moves)

    def _playout_after(self, state: GameState, first_move: Position, player: Player) -> float:
        sim_state = make_move(state, first_move)
        while sim_state.outcome is Outcome.IN_PROGRESS:
            move = self.rng.choice(available_moves(sim_state.board))
            sim_state = make_move(sim_state, move)
        if sim_state.outcome is Outcome.DRAW:
            return 0.5
        return 1.0 if sim_state.outcome.winner is player else 0.0


# Backward-compatible name; CLI flag remains ``mcts``.
MCTSAgent = MonteCarloRolloutAgent


AGENT_NAMES = (
    "human",
    "random",
    "heuristic",
    "minimax",
    "minimax-easy",
    "minimax-medium",
    "minimax-hard",
    "mcts",
)


def create_agent(
    name: str,
    *,
    seed: int | None = None,
    minimax_depth: int | None = None,
    mcts_simulations: int = 200,
) -> Agent:
    normalized = name.lower()
    rng = random.Random(seed)
    if normalized == "human":
        return HumanAgent()
    if normalized == "random":
        return RandomAgent(rng)
    if normalized == "heuristic":
        return HeuristicAgent(rng)
    if normalized in {"minimax", "minimax-hard"}:
        return MinimaxAgent(depth=minimax_depth, rng=rng)
    if normalized == "minimax-easy":
        return MinimaxAgent.easy(rng)
    if normalized == "minimax-medium":
        return MinimaxAgent.medium(rng)
    if normalized == "mcts":
        return MonteCarloRolloutAgent(simulations=mcts_simulations, rng=rng)
    choices = ", ".join(AGENT_NAMES)
    raise ValueError(f"Unknown agent {name!r}. Choices: {choices}")
