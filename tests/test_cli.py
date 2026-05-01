"""Test CLI commands."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from tictactoe.cli import main


class CliTests(unittest.TestCase):
    def test_tournament_command_prints_summary(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            code = main(["tournament", "--x", "minimax", "--o", "random", "--games", "2", "--seed", "3"])

        self.assertEqual(code, 0)
        self.assertIn("Tournament: minimax (X) vs random (O)", output.getvalue())
        self.assertIn("Games: 2", output.getvalue())


if __name__ == "__main__":
    unittest.main()

