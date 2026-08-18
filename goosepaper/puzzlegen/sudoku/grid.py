"""Generation of complete, valid Sudoku solution grids."""

from __future__ import annotations

import random

from .rules import Grid, box_size_to_n, cell_ok


def generate_solution(box_size: int, rng: random.Random | None = None) -> Grid:
    """Generate a random, fully filled, valid Sudoku grid.

    Args:
        box_size: Edge length of a box (3 for classic 9x9 Sudoku).
        rng: Optional ``random.Random`` instance for reproducible output.
    """
    if box_size < 2:
        raise ValueError("box_size must be >= 2")

    rng = rng or random.Random()
    n = box_size_to_n(box_size)
    grid: Grid = [[None] * n for _ in range(n)]
    positions = [(r, c) for r in range(n) for c in range(n)]

    if not _fill(grid, 0, positions, box_size, rng):
        raise RuntimeError("could not generate a valid Sudoku grid")
    return grid


def _fill(grid: Grid, idx: int, positions: list[tuple[int, int]], box_size: int, rng: random.Random) -> bool:
    if idx == len(positions):
        return True

    row, col = positions[idx]
    n = box_size_to_n(box_size)
    values = list(range(n))
    rng.shuffle(values)

    for value in values:
        grid[row][col] = value
        if cell_ok(grid, row, col, box_size):
            if _fill(grid, idx + 1, positions, box_size, rng):
                return True
        grid[row][col] = None

    return False
