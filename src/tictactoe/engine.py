"""Pure game rules and state transitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import cache

from .exceptions import GameOverError, InvalidMoveError, OutOfBoundsError
from .models import Board, GameState, Move, Outcome, Player, Position, WinCondition


@dataclass(frozen=True)
class GameCheck:
    outcome: Outcome
    winning_line: WinCondition | None = None


def available_moves(board: Board) -> list[Position]:
    return [position for position in board.positions() if board.at(position) is Player.NONE]


@cache
def all_line_positions(size: int, k: int) -> tuple[tuple[Position, ...], ...]:
    directions = ((0, 1), (1, 0), (1, 1), (1, -1))
    lines: list[tuple[Position, ...]] = []
    for row in range(size):
        for col in range(size):
            for d_row, d_col in directions:
                end_row = row + (k - 1) * d_row
                end_col = col + (k - 1) * d_col
                if 0 <= end_row < size and 0 <= end_col < size:
                    lines.append(
                        tuple(Position(row + step * d_row, col + step * d_col) for step in range(k))
                    )
    return tuple(lines)


def check_winner(board: Board, *, misere: bool = False) -> GameCheck:
    for line in all_line_positions(board.size, board.k):
        marks = tuple(board.at(position) for position in line)
        first = marks[0]
        if first is not Player.NONE and all(mark is first for mark in marks):
            winner = first.opponent if misere else first
            return GameCheck(
                outcome=Outcome.for_winner(winner),
                winning_line=WinCondition(player=first, positions=line),
            )
    if board.is_full:
        return GameCheck(outcome=Outcome.DRAW)
    return GameCheck(outcome=Outcome.IN_PROGRESS)


def make_move(state: GameState, position: Position) -> GameState:
    if state.outcome is not Outcome.IN_PROGRESS:
        raise GameOverError(f"Game is already over: {state.outcome.value}")
    if position.row >= state.board.size or position.col >= state.board.size:
        raise OutOfBoundsError(f"{position} is outside a {state.board.size}x{state.board.size} board")

    new_board = state.board.place(state.next_player, position)
    move = Move.create(
        player=state.next_player,
        position=position,
        move_number=len(state.history) + 1,
    )
    check = check_winner(new_board, misere=state.misere)
    next_player = state.next_player.opponent if check.outcome is Outcome.IN_PROGRESS else state.next_player
    return replace(
        state,
        board=new_board,
        next_player=next_player,
        history=(*state.history, move),
        outcome=check.outcome,
        winning_line=check.winning_line,
    )


def abandon(state: GameState) -> GameState:
    return replace(state, outcome=Outcome.ABANDONED)


def _apply_recorded_move(state: GameState, move: Move) -> GameState:
    if move.player is not state.next_player:
        raise InvalidMoveError(
            f"Move {move.move_number} expected {state.next_player.value}, got {move.player.value}"
        )
    if state.outcome is not Outcome.IN_PROGRESS:
        raise GameOverError(f"Move {move.move_number} appears after terminal state")
    new_board = state.board.place(move.player, move.position)
    check = check_winner(new_board, misere=state.misere)
    next_player = move.player.opponent if check.outcome is Outcome.IN_PROGRESS else move.player
    return replace(
        state,
        board=new_board,
        next_player=next_player,
        history=(*state.history, move),
        outcome=check.outcome,
        winning_line=check.winning_line,
    )


def replay(
    history: tuple[Move, ...] | list[Move],
    *,
    size: int = 3,
    k: int = 3,
    misere: bool = False,
    started_at: float | None = None,
) -> GameState:
    state = (
        GameState.new(size=size, k=k, misere=misere)
        if started_at is None
        else GameState(board=Board.empty(size=size, k=k), misere=misere, started_at=started_at)
    )
    for move in history:
        state = _apply_recorded_move(state, move)
    return state


def undo(state: GameState, plies: int = 1) -> GameState:
    if plies <= 0:
        return state
    kept_history = state.history[: max(0, len(state.history) - plies)]
    return replay(
        kept_history,
        size=state.board.size,
        k=state.board.k,
        misere=state.misere,
        started_at=state.started_at,
    )
