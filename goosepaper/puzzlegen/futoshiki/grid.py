"""Generation of complete, valid Futoshiki solution grids (Latin squares).

No inequality constraints are considered here -- those only get derived
from the finished solution afterwards (see ``puzzle.py``), so a full
solution is just a plain randomized Latin square, same approach as Sudoku's
``grid.py`` minus the box check.
"""

from __future__ import annotations

import random

from .rules import Grid, col_ok, row_ok


def generate_solution(size: int, rng: random.Random | None = None) -> Grid:
    """Generate a random, fully filled, valid Futoshiki Latin square.

    Args:
        size: Edge length of the grid.
        rng: Optional ``random.Random`` instance for reproducible output.
    """
    if size < 3:
        raise ValueError("size must be >= 3")

    rng = rng or random.Random()
    grid: Grid = [[None] * size for _ in range(size)]
    positions = [(r, c) for r in range(size) for c in range(size)]

    if not _fill(grid, 0, positions, size, rng):
        raise RuntimeError("could not generate a valid Futoshiki grid")
    return grid


def _fill(grid: Grid, idx: int, positions: list[tuple[int, int]], size: int, rng: random.Random) -> bool:
    if idx == len(positions):
        return True

    row, col = positions[idx]
    values = list(range(size))
    rng.shuffle(values)

    for value in values:
        grid[row][col] = value
        if row_ok(grid, row) and col_ok(grid, col):
            if _fill(grid, idx + 1, positions, size, rng):
                return True
        grid[row][col] = None

    return False
