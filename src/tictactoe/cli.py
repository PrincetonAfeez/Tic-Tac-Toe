"""Argparse command line interface."""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .agents import AGENT_NAMES, Agent, HumanAgent, MinimaxAgent, create_agent, parse_position
from .config import load_config
from .display import Display
from .engine import abandon, make_move, undo
from .exceptions import GameError
from .models import GameState, Outcome, Player
from .persistence import JsonGameRepository, StatsRepository
from .renderers import COLOR_SCHEMES, create_renderer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tictactoe",
        description="Immutable Tic-Tac-Toe with human, heuristic, minimax, and Monte Carlo rollout agents.",
    )
    subparsers = parser.add_subparsers(dest="command")

    play = subparsers.add_parser("play", help="start an interactive game")
    _add_game_options(play)
    play.add_argument("--clear", action="store_true", help="clear the terminal between frames")
    play.set_defaults(func=cmd_play)

    watch = subparsers.add_parser("watch", help="watch two agents play")
    _add_game_options(watch, default_x="minimax", default_o="heuristic")
    watch.add_argument("--delay", type=float, default=0.5, help="seconds between AI moves")
    watch.add_argument("--clear", action="store_true", help="clear the terminal between frames")
    watch.set_defaults(func=cmd_watch)

    tournament = subparsers.add_parser("tournament", help="run many games between two agents")
    _add_game_options(tournament, default_x="minimax", default_o="heuristic")
    tournament.add_argument("--games", type=int, default=100, help="number of games to run")
    tournament.set_defaults(func=cmd_tournament)

    replay_cmd = subparsers.add_parser("replay", help="step through a saved game")
    replay_cmd.add_argument("save_file", help="path or save name")
    replay_cmd.add_argument("--renderer", choices=("classic", "coordinate", "minimal", "big"))
    replay_cmd.add_argument("--colors", choices=tuple(COLOR_SCHEMES))
    replay_cmd.add_argument("--no-color", action="store_true", default=None)
    replay_cmd.add_argument("--no-pause", action="store_true", help="print all replay frames")
    replay_cmd.set_defaults(func=cmd_replay)

    stats = subparsers.add_parser("stats", help="show aggregate agent stats")
    stats.set_defaults(func=cmd_stats)

    analyze = subparsers.add_parser("analyze", help="compare each saved move to minimax")
    analyze.add_argument("save_file", help="path or save name")
    analyze.add_argument("--depth", type=int, default=None, help="optional minimax depth limit")
    analyze.set_defaults(func=cmd_analyze)

    parser.set_defaults(func=cmd_play)
    return parser


def _add_game_options(
    parser: argparse.ArgumentParser,
    *,
    default_x: str | None = None,
    default_o: str | None = None,
) -> None:
    parser.add_argument("--x", choices=AGENT_NAMES, default=default_x, help="agent for X")
    parser.add_argument("--o", choices=AGENT_NAMES, default=default_o, help="agent for O")
    parser.add_argument("--size", type=int, default=None, help="board size")
    parser.add_argument("--k", type=int, default=None, help="marks in a row needed to win")
    parser.add_argument("--misere", action="store_true", default=None, help="line-maker loses")
    parser.add_argument("--renderer", choices=("classic", "coordinate", "minimal", "big"))
    parser.add_argument("--colors", choices=tuple(COLOR_SCHEMES))
    parser.add_argument("--no-color", action="store_true", default=None)
    parser.add_argument("--input-mode", choices=("keypad", "arrow"), default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--minimax-depth", type=int, default=None)
    parser.add_argument("--mcts-simulations", type=int, default=None)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if not raw_args:
        raw_args = ["play"]
    args = parser.parse_args(raw_args)
    try:
        config = load_config()
        return int(args.func(args, config))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except (GameError, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def cmd_play(args: argparse.Namespace, config: dict[str, Any]) -> int:
    options = _game_options(args, config)
    state = GameState.new(size=options["size"], k=options["k"], misere=options["misere"])
    x_agent, o_agent = _create_agents(args, config, options["size"])
    renderer = create_renderer(options["renderer"], colors=options["colors"], no_color=options["no_color"])
    display = Display(renderer, clear_each_frame=bool(getattr(args, "clear", False)))
    repository = JsonGameRepository()
    stats = StatsRepository()
    final_state = _run_game(
        state,
        x_agent=x_agent,
        o_agent=o_agent,
        display=display,
        repository=repository,
        stats=stats,
        delay=0.0,
        interactive=True,
    )
    print(_final_summary(final_state))
    return 0


def cmd_watch(args: argparse.Namespace, config: dict[str, Any]) -> int:
    options = _game_options(args, config)
    x_agent, o_agent = _create_agents(args, config, options["size"])
    _reject_humans(x_agent, o_agent, "watch")
    state = GameState.new(size=options["size"], k=options["k"], misere=options["misere"])
    renderer = create_renderer(options["renderer"], colors=options["colors"], no_color=options["no_color"])
    display = Display(renderer, clear_each_frame=bool(args.clear))
    final_state = _run_game(
        state,
        x_agent=x_agent,
        o_agent=o_agent,
        display=display,
        repository=JsonGameRepository(),
        stats=StatsRepository(),
        delay=max(0.0, args.delay),
        interactive=False,
    )
    print(_final_summary(final_state))
    return 0


def cmd_tournament(args: argparse.Namespace, config: dict[str, Any]) -> int:
    if args.games < 1:
        raise ValueError("--games must be at least 1")
    options = _game_options(args, config)
    x_name = args.x or config["agents"]["x"]
    o_name = args.o or config["agents"]["o"]
    if "human" in {x_name, o_name}:
        raise ValueError("tournament does not support human agents")

    outcomes: Counter[str] = Counter()
    moves_total = 0
    for game_number in range(args.games):
        x_agent, o_agent = _create_agents(args, config, options["size"], seed_offset=game_number * 2)
        state = GameState.new(size=options["size"], k=options["k"], misere=options["misere"])
        final_state = _auto_play(state, x_agent=x_agent, o_agent=o_agent)
        outcomes[final_state.outcome.value] += 1
        moves_total += final_state.move_count

    print(f"Tournament: {x_name} (X) vs {o_name} (O)")
    print(f"Games: {args.games}")
    for outcome in (Outcome.X_WINS, Outcome.O_WINS, Outcome.DRAW, Outcome.ABANDONED):
        print(f"{outcome.value}: {outcomes[outcome.value]}")
    print(f"Average moves: {moves_total / args.games:.2f}")
    return 0


def cmd_replay(args: argparse.Namespace, config: dict[str, Any]) -> int:
    repository = JsonGameRepository()
    saved = repository.load(args.save_file)
    renderer_name = args.renderer or config["display"]["renderer"]
    colors = args.colors or config["display"]["colors"]
    no_color = _coalesce(args.no_color, config["display"]["no_color"])
    display = Display(create_renderer(renderer_name, colors=colors, no_color=no_color))

    state = GameState.new(size=saved.board.size, k=saved.board.k, misere=saved.misere)
    display.draw(state)
    if not args.no_pause:
        input("Press Enter for first move...")
    for move in saved.history:
        state = make_move(state, move.position)
        display.draw(state)
        if not args.no_pause and move is not saved.history[-1]:
            input("Press Enter for next move...")
    print(_final_summary(state))
    return 0


def cmd_stats(args: argparse.Namespace, config: dict[str, Any]) -> int:
    del args, config
    stats = StatsRepository().load()
    if not stats:
        print("No completed games recorded yet.")
        return 0
    print("Agent stats")
    for agent, values in sorted(stats.items()):
        print(
            f"{agent:16} wins={values.get('wins', 0):4} "
            f"losses={values.get('losses', 0):4} draws={values.get('draws', 0):4}"
        )
    return 0


def cmd_analyze(args: argparse.Namespace, config: dict[str, Any]) -> int:
    del config
    saved = JsonGameRepository().load(args.save_file)
    state = GameState.new(size=saved.board.size, k=saved.board.k, misere=saved.misere)
    advisor = MinimaxAgent(depth=args.depth)
    print(f"Analyzing {len(saved.history)} moves with minimax")
    for move in saved.history:
        recommendation = advisor.choose_move(state)
        marker = "OK" if recommendation == move.position else "DIFF"
        print(
            f"{move.move_number:02}. {move.player.value}@{move.position} "
            f"best={recommendation} {marker}"
        )
        state = make_move(state, move.position)
    print(_final_summary(state))
    return 0


def _game_options(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    size = _coalesce(args.size, config["board"]["size"])
    k = _coalesce(args.k, config["board"]["k"])
    if size > 3 and args.minimax_depth is None and config["ai"]["minimax_depth"] is None:
        config["ai"]["minimax_depth"] = 4
    return {
        "size": size,
        "k": k,
        "misere": _coalesce(args.misere, config["board"]["misere"]),
        "renderer": _coalesce(args.renderer, config["display"]["renderer"]),
        "colors": _coalesce(args.colors, config["display"]["colors"]),
        "no_color": _coalesce(args.no_color, config["display"]["no_color"]),
        "input_mode": _coalesce(args.input_mode, config["input"]["mode"]),
    }


def _coalesce(value: Any, fallback: Any) -> Any:
    return fallback if value is None else value


def _create_agents(
    args: argparse.Namespace,
    config: dict[str, Any],
    size: int,
    *,
    seed_offset: int = 0,
) -> tuple[Agent, Agent]:
    x_name = args.x or config["agents"]["x"]
    o_name = args.o or config["agents"]["o"]
    depth = _coalesce(args.minimax_depth, config["ai"]["minimax_depth"])
    if size > 3 and depth is None:
        depth = 4
    simulations = _coalesce(args.mcts_simulations, config["ai"]["mcts_simulations"])
    seed = args.seed
    x_seed = None if seed is None else seed + seed_offset
    o_seed = None if seed is None else seed + seed_offset + 1
    return (
        create_agent(x_name, seed=x_seed, minimax_depth=depth, mcts_simulations=simulations),
        create_agent(o_name, seed=o_seed, minimax_depth=depth, mcts_simulations=simulations),
    )


def _reject_humans(x_agent: Agent, o_agent: Agent, command: str) -> None:
    if isinstance(x_agent, HumanAgent) or isinstance(o_agent, HumanAgent):
        raise ValueError(f"{command} requires AI agents; use play for human games")


def _run_game(
    state: GameState,
    *,
    x_agent: Agent,
    o_agent: Agent,
    display: Display,
    repository: JsonGameRepository,
    stats: StatsRepository,
    delay: float,
    interactive: bool,
) -> GameState:
    while state.outcome is Outcome.IN_PROGRESS:
        display.draw(state)
        agent = x_agent if state.next_player is Player.X else o_agent
        if isinstance(agent, HumanAgent):
            state = _human_turn(
                state,
                repository=repository,
                display=display,
            )
        else:
            print(f"{state.next_player.value} ({agent.name}) thinking...")
            position = agent.choose_move(state)
            print(f"{state.next_player.value} -> {position}")
            state = make_move(state, position)
            if agent.last_stats is not None:
                print(f"{agent.name}: {agent.last_stats}")
            if delay:
                time.sleep(delay)
        if not interactive and delay:
            print()
    display.draw(state)
    stats.record_game(state, x_agent=x_agent.name, o_agent=o_agent.name)
    return state


def _human_turn(
    state: GameState,
    *,
    repository: JsonGameRepository,
    display: Display,
) -> GameState:
    while True:
        token = input(f"{state.next_player.value} move [A1, 7, h, u, r, s, l, q]: ").strip()
        command = token.lower()
        if command in {"h", "?", "help"}:
            print(_help_text())
            continue
        if command in {"q", "quit", "exit"}:
            if _confirm("Save before quitting?"):
                path = repository.save(state, name=input("Save name: ").strip() or None)
                print(f"Saved {path}")
            return abandon(state)
        if command in {"u", "undo"}:
            plies = 2 if state.move_count > 1 else 1
            return undo(state, plies=plies)
        if command in {"r", "restart"}:
            return GameState.new(size=state.board.size, k=state.board.k, misere=state.misere)
        if command in {"s", "save"}:
            path = repository.save(state, name=input("Save name: ").strip() or None)
            print(f"Saved {path}")
            continue
        if command in {"l", "load"}:
            saves = repository.list()
            if not saves:
                print("No saves found.")
                continue
            for index, path in enumerate(saves, start=1):
                print(f"{index}. {path.name}")
            choice = input("Load save number or path: ").strip()
            try:
                selected = saves[int(choice) - 1] if choice.isdigit() else Path(choice)
                return repository.load(selected)
            except (IndexError, FileNotFoundError, ValueError) as exc:
                print(f"Could not load save: {exc}")
                continue
        if command in {"hint"}:
            advisor = MinimaxAgent(depth=4 if state.board.size > 3 else None)
            print(f"Hint: {advisor.choose_move(state)}")
            continue
        try:
            return make_move(state, parse_position(token, state.board.size))
        except (GameError, ValueError) as exc:
            print(exc)
            display.draw(state)


def _help_text() -> str:
    return "\n".join(
        [
            "Commands:",
            "  A1 / 1A / row,col / keypad number  place a move",
            "  h or ?                              show this help",
            "  hint                                show a minimax hint",
            "  u                                   undo two plies, or one if only one exists",
            "  r                                   restart this match",
            "  s                                   save game",
            "  l                                   load game",
            "  q                                   quit",
        ]
    )


def _confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}


def _auto_play(state: GameState, *, x_agent: Agent, o_agent: Agent) -> GameState:
    while state.outcome is Outcome.IN_PROGRESS:
        agent = x_agent if state.next_player is Player.X else o_agent
        state = make_move(state, agent.choose_move(state))
    return state


def _final_summary(state: GameState) -> str:
    if state.outcome is Outcome.DRAW:
        result = "Game ended in a draw."
    elif state.outcome is Outcome.ABANDONED:
        result = "Game abandoned."
    else:
        winner = state.outcome.winner
        result = f"{winner.value} wins." if winner is not None else state.outcome.value
    return f"{result} Moves: {state.move_count}."


if __name__ == "__main__":
    raise SystemExit(main())
