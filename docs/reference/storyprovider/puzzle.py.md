# Logic puzzles

The `puzzle` source generates one or more logic puzzles - Sudoku, Binoxxo, Futoshiki,
Kakuro, or Shikaku - and renders each as plain HTML/CSS (no images). Every puzzle's
solution is generated too and collected separately in the paper's appendix.

## Configuration

```json
{ "type": "puzzle", "puzzle_type": "sudoku", "difficulty": "hard", "count": 2, "explanation": "footer", "name": "Sudoku" }
```

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `puzzle_type` | Yes | — | `sudoku`, `binoxxo`, `futoshiki`, `kakuro`, or `shikaku`. No default on purpose - a config that forgets it fails loudly instead of silently always generating Sudoku. |
| `box_size` | No | `3` | **Sudoku only**, ignored for every other type. `2` (4x4, a quick/easy variant) or `3` (the classic 9x9, 3x3 boxes). Unlike every other type's grid size, this does not vary by `difficulty` - all three difficulties use the same box size. |
| `difficulty` | No | `medium` | `easy`, `medium`, or `hard`. Controls how many cells/constraints are given, and (for every type but sudoku) the grid size itself - see e.g. `goosepaper/puzzlegen/binoxxo/config.py`'s `DIFFICULTIES` table. Grid size and difficulty aren't independent knobs: Shikaku's `hard` preset, for example, is specifically tuned for a 20x20 grid, so there's no separate `size` option to set independently. |
| `count` | No | `1` | How many puzzle instances of this `puzzle_type`+`difficulty` to generate. |
| `seed` | No | random | RNG seed, for reproducible generation. |
| `explanation` | No | `none` | `none`, `inline` (a short rules blurb repeated under every puzzle instance), `footer` (a real CSS footnote at the bottom of whichever page it lands on - one footnote per `puzzle_type` in the whole paper), or `appendix` (one rules blurb per `puzzle_type`, grouped with the solutions at the end of the document). |
| `name` | No | — | Visible heading for this puzzle instance (and its solution, suffixed " - Solution"). If omitted, no heading renders for the puzzle itself - only the enclosing section's own title identifies it. Useful when several different puzzle types share one section; redundant (and best left unset) when a section already covers exactly one type+difficulty. |

## Solutions and explanations

Every puzzle instance's solution is always generated, regardless of `explanation`, and
placed in the paper's appendix (`PlacementPreference.APPENDIX`) alongside every other
puzzle solution in the document rather than immediately following its own puzzle.

`explanation` is unrelated to the solution - it only controls whether/where a short
"how does this puzzle type work" rules blurb appears. Deduplication means only one
blurb per `puzzle_type` exists per document even with multiple instances/difficulties
configured.

## Puzzle types

- `sudoku`: classic 9x9 (or 4x4 with `box_size: 2`) grid, numbers 1-9 (or 1-4) unique
  per row, column, and box.
- `binoxxo`: grid filled with X/O, no more than two of the same symbol adjacent, equal
  counts per row/column, no repeated row or column.
- `futoshiki`: grid filled with unique numbers per row/column, satisfying inequality
  signs between neighboring cells.
- `kakuro`: white cells filled with digits 1-9 summing to each block's clue, no digit
  repeated within a block.
- `shikaku`: grid divided into rectangles, each containing exactly one number matching
  its own area.
