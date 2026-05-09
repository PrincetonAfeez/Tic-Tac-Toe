"""Property-based checks for the engine (Hypothesis + unittest for dual runners)."""

from __future__ import annotations

import unittest

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from tictactoe.engine import available_moves, make_move, undo
from tictactoe.models import Board, GameState, Outcome, Position


class EnginePropertyTests(unittest.TestCase):
    @settings(max_examples=60, deadline=None)
    @given(
        size=st.integers(min_value=3, max_value=6),
        k=st.integers(min_value=2, max_value=6),
    )
    def test_empty_board_has_all_cells_available(self, size: int, k: int) -> None:
        assume(k <= size)
        board = Board.empty(size=size, k=k)
        self.assertEqual(len(available_moves(board)), size * size)

    @settings(max_examples=80, deadline=None)
    @given(data=st.data())
    def test_random_legal_play_reaches_terminal(self, data: st.DataObject) -> None:
        state = GameState.new(size=3, k=3)
        while state.outcome is Outcome.IN_PROGRESS:
            moves = available_moves(state.board)
            pos = data.draw(st.sampled_from(moves), label="move")
            state = make_move(state, pos)
        self.assertTrue(state.outcome.is_terminal)

    @settings(max_examples=80, deadline=None)
    @given(data=st.data())
    def test_undo_replays_empty_state(self, data: st.DataObject) -> None:
        state = GameState.new(size=3, k=3)
        steps = data.draw(st.integers(min_value=0, max_value=9), label="steps")
        for _ in range(steps):
            if state.outcome is not Outcome.IN_PROGRESS:
                break
            moves = available_moves(state.board)
            pos = data.draw(st.sampled_from(moves), label="m")
            state = make_move(state, pos)
        plies = len(state.history)
        for _ in range(plies):
            state = undo(state)
        self.assertEqual(state.outcome, Outcome.IN_PROGRESS)
        self.assertEqual(state.move_count, 0)
        self.assertEqual(state.board.filled_count, 0)

    @settings(max_examples=100, deadline=None)
    @given(
        size=st.integers(min_value=3, max_value=8),
        row=st.integers(min_value=0, max_value=7),
        col=st.integers(min_value=0, max_value=7),
    )
    def test_position_index_roundtrip(self, size: int, row: int, col: int) -> None:
        assume(row < size and col < size)
        pos = Position(row, col)
        idx = pos.to_index(size)
        self.assertEqual(Position.from_index(idx, size), pos)


if __name__ == "__main__":
    unittest.main()
