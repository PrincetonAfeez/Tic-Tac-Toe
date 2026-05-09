# Algorithms

## Win Detection

The engine precomputes every contiguous line of length `k` for a board size:

- horizontal
- vertical
- diagonal down-right
- diagonal down-left

`check_winner` walks those lines and looks for one filled by the same player. For classic Tic-Tac-Toe this is the familiar eight lines. For `4x4, k=3` or `5x5, k=4`, the same code works without special cases.

## Heuristic Agent

The heuristic agent uses a classic priority list:

1. Win immediately if possible.
2. Block the opponent's immediate win.
3. Take the center.
4. Take a corner.
5. Pick any remaining legal move.

It is fast and readable, but not optimal.

## Minimax With Alpha-Beta

Minimax assumes both players choose their best available move. The current player maximizes the score; the opponent minimizes it.

Terminal scores are:

- win for the searching player: positive
- loss for the searching player: negative
- draw: zero

Depth is folded into terminal scoring so faster wins and slower losses are preferred.

Alpha-beta pruning skips branches that cannot change the final decision. Memoization stores evaluations by `(board, next_player, depth, target, misere)`, which works because `Board` is immutable and hashable.

On a 3x3 board with full depth, minimax is optimal and should never lose.

## Depth Limits

Full minimax is practical on 3x3. Larger boards grow quickly, so the CLI defaults minimax to a depth limit of `4` when the board is larger than 3x3 and no explicit depth is provided.

For non-terminal depth-limited leaves, the evaluator scores open lines:

- lines containing only the target player add points
- lines containing only the opponent subtract points
- blocked mixed lines are ignored

## Monte Carlo rollout (`mcts`)

The `MonteCarloRolloutAgent` is **not** full UCT or tree-structured MCTS. For each legal root move it runs random playouts to the end of the game and picks the move with the best average result.

It is intentionally simple: useful on larger boards where full minimax is expensive, and easy to compare against deterministic agents in tournament mode.

