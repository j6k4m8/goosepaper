"""Turn a Kakuro layout into a full puzzle: generate a black/white pattern,
find a witness digit fill, derive clue sums from it, and make sure the
result has exactly one solution.

Classic Kakuro has no numeric givens -- the pattern and clue sums alone are
supposed to pin down a unique fill. In practice, plenty of (pattern, sums)
combinations are *not* unique on their own (short runs in particular allow
several digit combinations for the same sum), and no amount of re-filling
the same pattern reliably fixes that -- see the ``_reveal_givens_until_unique``
docstring. So: try with zero givens first (the common case, especially for
sparser/harder patterns with longer runs); if that's ambiguous, reveal a
few solution cells as givens, in random order, until it becomes unique;
give up on this fill (try a fresh one, then a fresh layout) if that would
need revealing too large a fraction of the grid, since a puzzle that's
mostly-given isn't a real Kakuro puzzle anymore.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .config import DEFAULT_DIFFICULTY, DIFFICULTIES, Difficulty
from .grid import fill_values, generate_layout
from .rules import Grid, Run, canvas_size, with_target_sums
from .solver import SearchBudgetExceeded, count_solutions

MAX_FILL_ATTEMPTS = 10
MAX_LAYOUT_RETRIES = 8
# If more than this fraction of cells would need to be revealed to force
# uniqueness, reject the fill/layout instead of accepting a puzzle that's
# mostly pre-filled (measured empirically: layouts dominated by length-2
# runs can need >50% before becoming unique -- those are bad layouts, not
# just unlucky fills, and are better rejected than patched around).
MAX_GIVEN_FRACTION = 0.3


@dataclass
class Puzzle:
    size: int
    difficulty: str
    black: list[list[bool]]
    runs: list[Run]  # with target_sum set -- the fixed clues
    solution: Grid
    givens: Grid  # mostly None; a few revealed cells only when needed for uniqueness

    @property
    def grid_size(self) -> int:
        return canvas_size(self.size)


def _unique(runs: list[Run], n: int, given: Grid) -> bool:
    """``count_solutions`` treating an unresolved (budget-exceeded) search
    the same as "not proven unique yet" -- a few layouts (long runs, few
    givens) have a branching factor too large to fully explore, and it's
    both cheaper and safer to keep revealing more cells than to trust an
    unverified count (same conservative stance as Binoxxo's state.py)."""
    try:
        return count_solutions(runs, n, limit=2, initial=given) == 1
    except SearchBudgetExceeded:
        return False


def _reveal_givens_until_unique(runs: list[Run], n: int, solution: Grid, rng: random.Random) -> Grid | None:
    """Return a givens grid (subset of ``solution``) that makes ``runs``
    solve uniquely, or ``None`` if that would need more than
    ``MAX_GIVEN_FRACTION`` of the cells."""
    cells = sorted({cell for run in runs for cell in run.cells})
    given: Grid = [[None] * n for _ in range(n)]

    if _unique(runs, n, given):
        return given

    order = cells[:]
    rng.shuffle(order)
    max_givens = round(len(cells) * MAX_GIVEN_FRACTION)

    for count, (row, col) in enumerate(order, start=1):
        given[row][col] = solution[row][col]
        if _unique(runs, n, given):
            return given
        if count >= max_givens:
            return None
    return None


def generate_puzzle(
    size: int,
    difficulty: str | Difficulty = DEFAULT_DIFFICULTY,
    rng: random.Random | None = None,
) -> Puzzle:
    """Generate a Kakuro puzzle that has exactly one solution.

    A layout (black/white pattern) is generated, then a witness digit fill
    is found and its per-run sums adopted as the fixed clues. If the result
    doesn't solve uniquely as-is, a few cells are revealed as givens (see
    module docstring); if even that fails within budget, a fresh fill is
    tried against the *same* layout first (cheap), and only if that keeps
    failing is an entirely new layout generated.
    """
    rng = rng or random.Random()
    diff = DIFFICULTIES[difficulty] if isinstance(difficulty, str) else difficulty
    n = canvas_size(size)

    for _ in range(MAX_LAYOUT_RETRIES):
        black, bare_runs = generate_layout(size, diff.black_ratio, rng)

        for _ in range(MAX_FILL_ATTEMPTS):
            solution = fill_values(bare_runs, n, rng)
            runs = with_target_sums(bare_runs, solution)
            givens = _reveal_givens_until_unique(runs, n, solution, rng)
            if givens is not None:
                return Puzzle(size=size, difficulty=diff.name, black=black, runs=runs, solution=solution, givens=givens)

    raise RuntimeError(f"could not generate a unique {size}x{size} Kakuro puzzle")


def generate_puzzles(
    count: int,
    size: int,
    difficulty: str | Difficulty = DEFAULT_DIFFICULTY,
    rng: random.Random | None = None,
) -> list[Puzzle]:
    rng = rng or random.Random()
    return [generate_puzzle(size, difficulty, rng=rng) for _ in range(count)]
