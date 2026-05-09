"""Test engine functionality."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from tictactoe.engine import available_moves, make_move, undo
from tictactoe.exceptions import CellOccupiedError, GameOverError, OutOfBoundsError
from tictactoe.models import Board, GameState, Outcome, Player, Position


def play(moves: list[tuple[int, int]], *, size: int = 3, k: int = 3) -> GameState:
    state = GameState.new(size=size, k=k)
    for row, col in moves:
        state = make_move(state, Position(row, col))
    return state


class EngineTests(unittest.TestCase):
    def test_board_is_immutable(self) -> None:
        board = Board.empty()
        moved = board.place(Player.X, Position(0, 0))

        self.assertEqual(board.at(Position(0, 0)).value, ".")
        self.assertEqual(moved.at(Position(0, 0)).value, "X")
        with self.assertRaises(FrozenInstanceError):
            board.size = 4  # type: ignore[misc]
        with self.assertRaises(TypeError):
            board.cells[0] = moved.cells[0]  # type: ignore[index]

    def test_x_wins_row(self) -> None:
        state = play([(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)])

        self.assertEqual(state.outcome, Outcome.X_WINS)
        self.assertIsNotNone(state.winning_line)
        self.assertEqual([pos.label for pos in state.winning_line.positions], ["A1", "A2", "A3"])

    def test_generalized_four_by_four_k_three(self) -> None:
        state = play([(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)], size=4, k=3)

        self.assertEqual(state.outcome, Outcome.X_WINS)

    def test_draw(self) -> None:
        state = play(
            [
                (0, 0),
                (0, 1),
                (0, 2),
                (1, 0),
                (1, 2),
                (1, 1),
                (2, 0),
                (2, 2),
                (2, 1),
            ]
        )

        self.assertEqual(state.outcome, Outcome.DRAW)

    def test_invalid_moves_raise_specific_errors(self) -> None:
        state = GameState.new()
        state = make_move(state, Position(0, 0))

        with self.assertRaises(CellOccupiedError):
            make_move(state, Position(0, 0))
        with self.assertRaises(OutOfBoundsError):
            make_move(state, Position(4, 0))

        finished = play([(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)])
        with self.assertRaises(GameOverError):
            make_move(finished, Position(2, 2))

    def test_undo_make_move_returns_previous_state(self) -> None:
        state = GameState.new()
        moved = make_move(state, Position(1, 1))

        self.assertEqual(undo(moved), state)

    def test_available_moves_are_empty_cells(self) -> None:
        state = make_move(GameState.new(), Position(1, 1))
        moves = available_moves(state.board)

        self.assertEqual(len(moves), 8)
        self.assertNotIn(Position(1, 1), moves)

    def test_misere_line_maker_loses(self) -> None:
        state = GameState.new(misere=True)
        for move in [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]:
            state = make_move(state, Position(*move))

        self.assertEqual(state.outcome, Outcome.O_WINS)
        self.assertEqual(state.winning_line.player.value, "X")


if __name__ == "__main__":
    unittest.main()
