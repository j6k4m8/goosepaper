"""Rule checks shared by the solution generator and the solver.

A grid is a list of lists of size ``size x size`` containing ``0``..
``size-1`` or ``None`` (empty cell). Futoshiki is a Latin square (each row
and column contains every value exactly once) -- unlike Sudoku there are no
sub-boxes -- plus a fixed set of inequality constraints between certain
orthogonally adjacent cell pairs, which must hold once both cells are
filled. All checks here work on *partial* grids too, so they can be used
for early pruning during backtracking.
"""

from __future__ import annotations

from dataclasses import dataclass

Grid = list[list[int | None]]
Cell = tuple[int, int]


@dataclass(frozen=True)
class Constraint:
    """An inequality between two orthogonally adjacent cells: the value at
    ``lesser`` must end up strictly smaller than the value at ``greater``.

    Direction is normalized this way (rather than storing "<" vs. ">") so
    rendering can derive the on-page arrow orientation purely from the two
    cells' relative positions -- see ``modules.futoshiki.pdf``.
    """

    lesser: Cell
    greater: Cell


def _no_duplicates(values: list[int | None]) -> bool:
    seen = [v for v in values if v is not None]
    return len(seen) == len(set(seen))


def row_ok(grid: Grid, row: int) -> bool:
    return _no_duplicates(grid[row])


def col_ok(grid: Grid, col: int) -> bool:
    return _no_duplicates([r[col] for r in grid])


def constraint_ok(grid: Grid, constraint: Constraint) -> bool:
    lr, lc = constraint.lesser
    gr, gc = constraint.greater
    lesser_value = grid[lr][lc]
    greater_value = grid[gr][gc]
    if lesser_value is None or greater_value is None:
        return True
    return lesser_value < greater_value


def index_constraints(constraints: list[Constraint]) -> dict[Cell, list[Constraint]]:
    """Group constraints by each cell they touch, so backtracking only has
    to re-check the (few) constraints touching the just-placed cell."""
    index: dict[Cell, list[Constraint]] = {}
    for constraint in constraints:
        index.setdefault(constraint.lesser, []).append(constraint)
        index.setdefault(constraint.greater, []).append(constraint)
    return index


def cell_ok(grid: Grid, row: int, col: int, constraints_by_cell: dict[Cell, list[Constraint]]) -> bool:
    """Check row, column and inequality constraints touching ``(row, col)``."""
    if not row_ok(grid, row) or not col_ok(grid, col):
        return False
    return all(constraint_ok(grid, c) for c in constraints_by_cell.get((row, col), []))


def is_complete(grid: Grid) -> bool:
    return all(v is not None for row in grid for v in row)


def is_valid_solution(grid: Grid, constraints: list[Constraint]) -> bool:
    """Full validation of a completely filled grid."""
    size = len(grid)
    if not is_complete(grid):
        return False
    if not all(row_ok(grid, r) for r in range(size)):
        return False
    if not all(col_ok(grid, c) for c in range(size)):
        return False
    return all(constraint_ok(grid, c) for c in constraints)
