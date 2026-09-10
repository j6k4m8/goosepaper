"""Rule checks shared by the solution generator and the solver.

A grid is a list of lists of size ``n x n`` (``n = box_size**2``) containing
``0``..``n-1`` or ``None`` (empty cell). All checks here are written to work
on *partial* grids as well, so they can be used for early pruning during
backtracking:

- Each row contains every value at most once.
- Each column contains every value at most once.
- Each ``box_size x box_size`` box contains every value at most once.

Unlike Binoxxo, Sudoku's constraints only forbid duplicates among already
placed cells, so they can be checked immediately after placing a value -
no deferred "line is complete" bookkeeping is needed.
"""

from __future__ import annotations

Grid = list[list[int | None]]


def box_size_to_n(box_size: int) -> int:
    return box_size * box_size


def _no_duplicates(values: list[int | None]) -> bool:
    seen = [v for v in values if v is not None]
    return len(seen) == len(set(seen))


def row_ok(grid: Grid, row: int) -> bool:
    return _no_duplicates(grid[row])


def col_ok(grid: Grid, col: int) -> bool:
    return _no_duplicates([r[col] for r in grid])


def box_ok(grid: Grid, row: int, col: int, box_size: int) -> bool:
    box_row = (row // box_size) * box_size
    box_col = (col // box_size) * box_size
    values = [
        grid[r][c]
        for r in range(box_row, box_row + box_size)
        for c in range(box_col, box_col + box_size)
    ]
    return _no_duplicates(values)


def cell_ok(grid: Grid, row: int, col: int, box_size: int) -> bool:
    """Check row, column and box constraints around a just-placed cell."""
    return row_ok(grid, row) and col_ok(grid, col) and box_ok(grid, row, col, box_size)


def is_complete(grid: Grid) -> bool:
    return all(v is not None for row in grid for v in row)


def is_valid_solution(grid: Grid, box_size: int) -> bool:
    """Full validation of a completely filled grid."""
    n = box_size_to_n(box_size)
    if not is_complete(grid):
        return False
    if not all(row_ok(grid, r) for r in range(n)):
        return False
    if not all(col_ok(grid, c) for c in range(n)):
        return False
    if not all(
        box_ok(grid, r, c, box_size)
        for r in range(0, n, box_size)
        for c in range(0, n, box_size)
    ):
        return False
    return True
