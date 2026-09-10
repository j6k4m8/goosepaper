"""Count how many solutions a Kakuro layout (with fixed clue sums, and
optionally some cells already given) has.

Used by :mod:`goosepaper.puzzlegen.kakuro.puzzle` to make sure a
generated puzzle -- fixed black/white pattern, fixed clue sums, and
whichever cells (if any) are revealed as numeric givens -- has exactly one
valid digit fill before it's accepted.
"""

from __future__ import annotations

from .rules import Cell, Grid, Run, cell_ok, ordered_cells, run_candidate_digits, runs_by_cell

# Layouts with several long (5-6 cell) runs and few givens can have a huge
# branching factor -- observed hanging for tens of seconds on a single
# count_solutions call for one particular 6x6 layout dominated by
# length-6 runs, even with combination-table pruning and forward-checking
# (see rules.py/solver.py and AGENTS.md). Rather than let that block
# generation, cap the search and let the caller treat "budget exceeded" the
# same as "not proven unique yet" -- puzzle.py's given-revealing loop just
# keeps revealing more cells (which shrinks the remaining search each time)
# instead of trusting an unverified count. Raised from 20,000 to 50,000
# once generation started producing 6x6/7x7 layouts (see grid.py's
# MAX_RUN_LENGTH_AFTER_SPLIT): fewer individual count_solutions calls give
# up right before they would have resolved, at the cost of the worst
# unresolved calls taking a bit longer.
DEFAULT_NODE_BUDGET = 50_000


class SearchBudgetExceeded(Exception):
    """Raised when a search exceeds its node budget without resolving."""


def count_solutions(
    runs: list[Run],
    n: int,
    limit: int = 2,
    initial: Grid | None = None,
    max_nodes: int | None = DEFAULT_NODE_BUDGET,
) -> int:
    """``initial``, if given, pre-fills some cells (their values are taken
    as fixed givens, not branched on) -- used to check whether revealing a
    few cells is enough to make an otherwise-ambiguous (pattern, sums)
    combination unique. Defaults to a fully empty grid.

    Raises ``SearchBudgetExceeded`` if ``max_nodes`` is given and the
    search doesn't finish within it -- callers that can't afford to block
    indefinitely should catch this and treat the result as unresolved
    rather than assuming any particular count.
    """
    grid: Grid = [row[:] for row in initial] if initial is not None else [[None] * n for _ in range(n)]
    all_cells = ordered_cells(runs)
    empty_cells = [cell for cell in all_cells if grid[cell[0]][cell[1]] is None]
    index = runs_by_cell(runs)
    node_budget = [max_nodes] if max_nodes is not None else None
    return _count(grid, 0, empty_cells, index, limit, node_budget)


def _count(
    grid: Grid,
    idx: int,
    cells: list[Cell],
    index: dict[Cell, list[Run]],
    limit: int,
    node_budget: list[int] | None,
) -> int:
    if node_budget is not None:
        node_budget[0] -= 1
        if node_budget[0] <= 0:
            raise SearchBudgetExceeded

    if idx == len(cells):
        return 1

    row, col = cells[idx]
    runs_here = index.get((row, col), [])
    found = 0
    for value in _candidate_digits(grid, runs_here):
        grid[row][col] = value
        if cell_ok(grid, (row, col), runs_here) and _forward_check_ok(grid, runs_here, index):
            found += _count(grid, idx + 1, cells, index, limit, node_budget)
        if found >= limit:
            grid[row][col] = None
            return found
    grid[row][col] = None
    return found


def _candidate_digits(grid: Grid, runs_here: list[Run]) -> list[int]:
    """Digits worth trying at a cell: 1-9 restricted by the combination-
    table candidates (see ``rules.run_candidate_digits``) of every run
    touching the cell -- a run without a target yet (shouldn't happen once
    sums are fixed, but defensively handled) simply doesn't restrict."""
    candidates = set(range(1, 10))
    for run in runs_here:
        if not candidates:
            break  # a cell has at most 2 runs; no need to filter further once empty
        run_candidates = run_candidate_digits(run, grid)
        if run_candidates is not None:
            candidates &= run_candidates
    return sorted(candidates)


def _forward_check_ok(grid: Grid, runs_here: list[Run], index: dict[Cell, list[Run]]) -> bool:
    """After placing a value, verify every still-empty cell in the
    just-affected runs still has at least one legal candidate.

    ``ordered_cells`` visits cells most-constrained-first, so a run's own
    cells aren't necessarily adjacent in the search order -- without this,
    a placement that dooms a *later* cell in a long run (e.g. run.py:
    length 5-9 runs are exactly the hard case) only gets caught once
    backtracking finally reaches that cell, several branch levels deeper.
    Checking right away turns that into an immediate prune, which is what
    made ``count_solutions`` still slow for size 6-7/hard even after
    combination-table candidate restriction (see AGENTS.md)."""
    for run in runs_here:
        for cell in run.cells:
            if grid[cell[0]][cell[1]] is None and not _candidate_digits(grid, index.get(cell, [])):
                return False
    return True


def has_unique_solution(runs: list[Run], n: int, initial: Grid | None = None) -> bool:
    return count_solutions(runs, n, limit=2, initial=initial) == 1
