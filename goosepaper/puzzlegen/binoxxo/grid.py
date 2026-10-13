"""Generation of complete, valid Binoxxo solution grids."""

from __future__ import annotations

import random

from . import state
from .state import Grid

# Building a full solution from an empty board occasionally hits a deep
# blind-guess dead end (see state.SearchBudgetExceeded). Retrying from
# scratch with fresh randomness is cheap (the common case finishes in well
# under a second), so a generous retry count just makes generation robust
# without ever silently failing in practice.
MAX_ATTEMPTS = 50


def generate_solution(size: int, rng: random.Random | None = None) -> Grid:
    """Generate a random, fully filled, valid Binoxxo grid.

    Args:
        size: Edge length of the grid. Must be even (Binoxxo needs an equal
            number of 0s and 1s per row/column).
        rng: Optional ``random.Random`` instance for reproducible output.
    """
    if size % 2 != 0 or size < 4:
        raise ValueError("size must be an even number >= 4")

    rng = rng or random.Random()
    empty: Grid = [[None] * size for _ in range(size)]

    for _ in range(MAX_ATTEMPTS):
        try:
            solution = state.find_solution(empty, rng=rng, max_nodes=state.DEFAULT_NODE_BUDGET)
        except state.SearchBudgetExceeded:
            continue
        if solution is not None:
            return solution

    raise RuntimeError(f"could not generate a valid {size}x{size} Binoxxo grid after {MAX_ATTEMPTS} attempts")
