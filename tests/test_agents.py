"""Test Agents implementations."""

from __future__ import annotations

import random
import unittest

from tictactoe.agents import (
    HeuristicAgent,
    HumanAgent,
    MinimaxAgent,
    MonteCarloRolloutAgent,
    RandomAgent,
)
from tictactoe.engine import available_moves, make_move
from tictactoe.models import GameState, Outcome, Player, Position


def run_game(x_agent, o_agent) -> GameState:
    state = GameState.new()
    while state.outcome is Outcome.IN_PROGRESS:
        agent = x_agent if state.next_player is Player.X else o_agent
        state = make_move(state, agent.choose_move(state))
    return state


class AgentTests(unittest.TestCase):
    def test_random_agent_never_picks_occupied_cell(self) -> None:
        state = make_move(GameState.new(), Position(1, 1))
        move = RandomAgent(random.Random(7)).choose_move(state)

        self.assertIn(move, available_moves(state.board))

    def test_heuristic_takes_immediate_win(self) -> None:
        state = GameState.new()
        for move in [Position(0, 0), Position(1, 0), Position(0, 1), Position(1, 1)]:
            state = make_move(state, move)

        self.assertEqual(HeuristicAgent(random.Random(1)).choose_move(state), Position(0, 2))

    def test_heuristic_blocks_immediate_threat(self) -> None:
        state = GameState.new()
        for move in [Position(0, 0), Position(1, 0), Position(0, 1)]:
            state = make_move(state, move)

        self.assertEqual(HeuristicAgent(random.Random(1)).choose_move(state), Position(0, 2))

    def test_minimax_never_loses_to_random_as_x_or_o(self) -> None:
        for seed in range(20):
            as_x = run_game(MinimaxAgent(rng=random.Random(seed)), RandomAgent(random.Random(seed)))
            self.assertNotEqual(as_x.outcome, Outcome.O_WINS)

            as_o = run_game(RandomAgent(random.Random(seed)), MinimaxAgent(rng=random.Random(seed)))
            self.assertNotEqual(as_o.outcome, Outcome.X_WINS)

    def test_minimax_vs_minimax_draws(self) -> None:
        state = run_game(MinimaxAgent(rng=random.Random(1)), MinimaxAgent(rng=random.Random(2)))

        self.assertEqual(state.outcome, Outcome.DRAW)

    def test_human_agent_retries_on_bad_input_then_accepts(self) -> None:
        responses = iter(["nope", "A1"])

        def read_line(_prompt: str) -> str:
            return next(responses)

        echoed: list[object] = []

        def echo(msg: object) -> None:
            echoed.append(msg)

        agent = HumanAgent(read_line=read_line, echo=echo)
        move = agent.choose_move(GameState.new())

        self.assertEqual(move, Position(0, 0))
        self.assertEqual(len(echoed), 1)

    def test_monte_carlo_rollout_returns_legal_move(self) -> None:
        state = make_move(GameState.new(), Position(1, 1))
        move = MonteCarloRolloutAgent(simulations=40, rng=random.Random(0)).choose_move(state)

        self.assertIn(move, available_moves(state.board))


if __name__ == "__main__":
    unittest.main()

