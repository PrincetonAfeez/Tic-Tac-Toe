"""Test persistence functionality."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tictactoe.engine import make_move
from tictactoe.models import GameState, Position
from tictactoe.persistence import InMemoryGameRepository, JsonGameRepository


class PersistenceTests(unittest.TestCase):
    def test_json_repository_round_trips_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repository = JsonGameRepository(Path(tmp))
            state = make_move(GameState.new(), Position(1, 1))

            path = repository.save(state, name="center")
            loaded = repository.load(path)

            self.assertEqual(loaded, state)

    def test_in_memory_repository_round_trips_state(self) -> None:
        repository = InMemoryGameRepository()
        state = make_move(GameState.new(size=4, k=3), Position(0, 0))

        path = repository.save(state, name="memory")

        self.assertEqual(repository.load(path), state)


if __name__ == "__main__":
    unittest.main()

