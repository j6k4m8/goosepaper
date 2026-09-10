"""Count how many solutions a (partial) Binoxxo grid has.

Used by :mod:`goosepaper.puzzlegen.binoxxo.puzzle` to make sure a generated
puzzle has exactly one solution before cells are removed from the full grid.
The actual search (constraint propagation + minimal backtracking) lives in
:mod:`goosepaper.puzzlegen.binoxxo.state`; this module just exposes the
puzzle-facing API on top of it.
"""

from __future__ import annotations

from . import state
from .state import Grid


def count_solutions(grid: Grid, limit: int = 2, max_nodes: int | None = state.DEFAULT_NODE_BUDGET) -> int:
    """Count valid completions of ``grid``, stopping early once ``limit`` is reached.

    ``grid`` is not modified. If the search can't verify the count within
    ``max_nodes`` (see ``state.SearchBudgetExceeded``), this conservatively
    reports ``limit`` -- i.e. "not proven unique" -- rather than guessing.
    """
    return state.count_solutions(grid, limit, max_nodes=max_nodes)


def has_unique_solution(grid: Grid) -> bool:
    return count_solutions(grid, limit=2) == 1
