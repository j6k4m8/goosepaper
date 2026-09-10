"""Count how many solutions a (partial) Futoshiki grid has, given a fixed
set of inequality constraints.

Used by :mod:`goosepaper.puzzlegen.futoshiki.puzzle` to make sure a
generated puzzle has exactly one solution before numeric givens are removed
from the full grid. The constraint set itself never changes during that
process -- only which cells are pre-filled does.
"""

from __future__ import annotations

from .rules import Cell, Constraint, Grid, cell_ok


def count_solutions(grid: Grid, constraints_by_cell: dict[Cell, list[Constraint]], limit: int = 2) -> int:
    """Count valid completions of ``grid``, stopping early once ``limit`` is reached.

    ``grid`` is not modified.
    """
    work: Grid = [row[:] for row in grid]
    size = len(grid)
    empties = [(r, c) for r in range(size) for c in range(size) if work[r][c] is None]
    return _count(work, 0, empties, constraints_by_cell, size, limit)


def _count(
    grid: Grid,
    idx: int,
    empties: list[Cell],
    constraints_by_cell: dict[Cell, list[Constraint]],
    size: int,
    limit: int,
) -> int:
    if idx == len(empties):
        return 1

    row, col = empties[idx]
    found = 0
    for value in range(size):
        grid[row][col] = value
        if cell_ok(grid, row, col, constraints_by_cell):
            found += _count(grid, idx + 1, empties, constraints_by_cell, size, limit)
        if found >= limit:
            grid[row][col] = None
            return found
    grid[row][col] = None
    return found


def has_unique_solution(grid: Grid, constraints_by_cell: dict[Cell, list[Constraint]]) -> bool:
    return count_solutions(grid, constraints_by_cell, limit=2) == 1
