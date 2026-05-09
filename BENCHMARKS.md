# Benchmarks

Benchmarks can be regenerated from the project root after installation:

```powershell
tictactoe tournament --x minimax --o random --games 100 --seed 1
tictactoe tournament --x minimax --o heuristic --games 100 --seed 1
tictactoe tournament --x minimax --o minimax --games 50 --seed 1
```

Measured 3x3 results from this workspace:

| Matchup | Games | X wins | O wins | Draws | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| minimax X vs random O | 100 | 99 | 0 | 1 | Minimax did not lose |
| random X vs minimax O | 100 | 0 | 83 | 17 | Minimax did not lose |
| minimax X vs heuristic O | 100 | 19 | 0 | 81 | Heuristic blocks many threats |
| minimax X vs minimax O | 10 | 0 | 0 | 10 | Optimal play draws |

Exact win counts vary when an agent has randomized tie-breaking or random playouts. The invariant to watch is that full-depth minimax on 3x3 has zero losses.
