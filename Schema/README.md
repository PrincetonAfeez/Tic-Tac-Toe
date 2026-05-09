# Schema

Simple JSON Schema files for the Tic-Tac-Toe project.

## Files

| File | Purpose |
| --- | --- |
| `schema-index.json` | Catalog of the schema files in this folder. |
| `domain.schema.json` | Shared definitions for players, cells, positions, moves, boards, outcomes, win conditions, and full game state. |
| `game-save.schema.json` | Validates JSON save files written by `JsonGameRepository.save()`. |
| `stats.schema.json` | Validates aggregate stats at `~/.tictactoe/stats.json`. |
| `history-event.schema.json` | Validates one JSON object line from `~/.tictactoe/history.jsonl`. |
| `config.schema.json` | Documents and validates the parsed object shape of `~/.tictactoe/config.toml`. |

## Notes

- These schemas use JSON Schema Draft 2020-12.
- `config.schema.json` describes the TOML file after it has been parsed into an object.
- The `Board.cells` length should equal `size * size`. The schema strictly enforces this for common 3x3, 4x4, and 5x5 boards and documents the invariant for larger boards.
- Cross-field gameplay consistency, such as whose turn comes after a move history or whether a `winning_line` actually wins, remains application logic and is not fully enforced by JSON Schema.

## Example validation

```bash
python -m pip install check-jsonschema
check-jsonschema --schemafile Schema/game-save.schema.json path/to/save.json
check-jsonschema --schemafile Schema/stats.schema.json ~/.tictactoe/stats.json
```
