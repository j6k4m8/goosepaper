"""Rule checks and pure grid/run derivation for Kakuro.

Cells are either black (blocked, potentially carrying clue sums) or white
(fillable with a digit 1-9 -- stored directly as 1-9, not 0-indexed like
the other modules, since Kakuro's digit alphabet is always exactly 1-9
regardless of grid size, there's no size-dependent symbol alphabet to index
into). Row 0 and column 0 of the canvas are always black (they only exist
to hold clues for the first real row/column) -- the playable area is rows/
columns 1..size. A "run" is a maximal horizontal or vertical sequence of
consecutive white cells; within a run every digit must be distinct and the
digits must sum to the run's clue.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations

Grid = list[list[int | None]]
Cell = tuple[int, int]


@dataclass(frozen=True)
class Run:
    cells: tuple[Cell, ...]
    clue_cell: Cell  # the black cell holding this run's sum
    orientation: str  # "h" (row, sum shown top-right of clue cell) or "v" (column, bottom-left)
    target_sum: int | None = None  # unset while only establishing a witness fill, see grid.fill_values


def canvas_size(size: int) -> int:
    """Interior play area is size x size; the canvas adds one black border
    row/column for clues, so it is (size + 1) x (size + 1)."""
    return size + 1


def compute_runs(black: list[list[bool]]) -> list[Run]:
    """Derive every maximal horizontal and vertical white-cell run from a
    black/white layout, purely from the pattern (no values involved). May
    include runs shorter than 2 or longer than 9 cells -- callers validate
    that separately (see grid.py) rather than this silently filtering them,
    so a caller can't accidentally miss a malformed layout."""
    n = len(black)
    runs: list[Run] = []

    for row in range(n):
        col = 0
        while col < n:
            if black[row][col]:
                col += 1
                continue
            start = col
            while col < n and not black[row][col]:
                col += 1
            cells = tuple((row, c) for c in range(start, col))
            runs.append(Run(cells=cells, clue_cell=(row, start - 1), orientation="h"))

    for col in range(n):
        row = 0
        while row < n:
            if black[row][col]:
                row += 1
                continue
            start = row
            while row < n and not black[row][col]:
                row += 1
            cells = tuple((r, col) for r in range(start, row))
            runs.append(Run(cells=cells, clue_cell=(start - 1, col), orientation="v"))

    return runs


def runs_by_cell(runs: list[Run]) -> dict[Cell, list[Run]]:
    index: dict[Cell, list[Run]] = {}
    for run in runs:
        for cell in run.cells:
            index.setdefault(cell, []).append(run)
    return index


def has_invalid_run_length(runs: list[Run]) -> bool:
    return any(len(run.cells) < 2 or len(run.cells) > 9 for run in runs)


def ordered_cells(runs: list[Run]) -> list[Cell]:
    """All cells touched by any run, ordered by ascending minimum run
    length among the runs touching them (cells that are only ever part of
    short runs come first).

    This is a most-constrained-variable heuristic: a short run has far
    fewer valid digit combinations than a long one, so placing its cells
    first hits contradictions -- or pins down forced values -- much earlier
    than the naive row-major order. Without this, backtracking search over
    Kakuro is far too slow: unlike the other modules, a Kakuro puzzle has
    no numeric givens to bootstrap propagation from, so every cell starts
    completely unknown (observed: row-major order left many search calls
    still unresolved after a 20,000-node budget)."""
    index = runs_by_cell(runs)
    cells = list(index.keys())
    cells.sort(key=lambda cell: (min(len(run.cells) for run in index[cell]), cell))
    return cells


def with_target_sums(runs: list[Run], solution: Grid) -> list[Run]:
    """Return new ``Run``s with ``target_sum`` set to each run's actual sum
    in ``solution`` -- the fixed clue set a puzzle is built around."""
    result = []
    for run in runs:
        total = sum(solution[r][c] for r, c in run.cells)
        result.append(Run(cells=run.cells, clue_cell=run.clue_cell, orientation=run.orientation, target_sum=total))
    return result


def distinct_in_run(grid: Grid, run: Run) -> bool:
    values = [grid[r][c] for r, c in run.cells]
    seen = [v for v in values if v is not None]
    return len(seen) == len(set(seen))


def run_feasible(grid: Grid, run: Run) -> bool:
    """True while the run's target sum remains achievable, or once filled,
    is exactly met. Always true if the run has no target yet (the
    witness-fill phase, before sums are derived).

    Beyond the trivial "partial sum doesn't already exceed the target"
    check, this also bounds what the *remaining* cells could still sum to:
    with ``k`` cells left and ``available`` = digits 1-9 not yet used in
    this run, the achievable range is
    ``[sum of k smallest available, sum of k largest available]``. Without
    this bound, backtracking search is intractable -- unlike Sudoku/
    Futoshiki, Kakuro puzzles have no numeric givens, so every run starts
    completely unknown and plain distinctness pruning alone explores a huge
    space before hitting a contradiction (observed: generation hung
    indefinitely on a 6x6 without this check).
    """
    if run.target_sum is None:
        return True
    values = [grid[r][c] for r, c in run.cells]
    filled = [v for v in values if v is not None]
    used = set(filled)
    partial_sum = sum(filled)
    remaining_needed = run.target_sum - partial_sum
    remaining_count = len(values) - len(filled)

    if remaining_count == 0:
        return partial_sum == run.target_sum
    if remaining_needed < 0:
        return False

    available = sorted(d for d in range(1, 10) if d not in used)
    if len(available) < remaining_count:
        return False
    min_possible = sum(available[:remaining_count])
    max_possible = sum(available[-remaining_count:])
    return min_possible <= remaining_needed <= max_possible


@lru_cache(maxsize=None)
def run_combinations(length: int, target_sum: int) -> frozenset[frozenset[int]]:
    """Every set of ``length`` distinct digits from 1-9 summing to
    ``target_sum`` -- the standard real-world Kakuro solving technique
    (precomputed combination tables per run length/sum), used by
    ``run_candidate_digits`` to restrict which digits are even worth
    trying in a cell, instead of blindly trying 1-9 and pruning after the
    fact via ``run_feasible``'s min/max sum bound. Cached: there are only
    9 possible lengths and a small range of sums, so the whole table is
    tiny and reused across every run of the same shape."""
    return frozenset(
        frozenset(combo) for combo in combinations(range(1, 10), length) if sum(combo) == target_sum
    )


def run_candidate_digits(run: Run, grid: Grid) -> frozenset[int] | None:
    """Digits that could still legally fill an empty cell of ``run``, given
    its fixed target sum and whatever digits are already placed in it.

    This can only ever be a superset of the values a full backtracking
    search would eventually try (a digit not in this set appears in zero
    valid combinations for the run, so it's a genuine dead end), so
    intersecting a cell's candidates with this never rules out a real
    solution -- it just skips digits doomed to fail ``run_feasible``
    several placements later instead of immediately.

    Returns ``None`` if the run has no target yet (the witness-fill phase
    in ``grid.py``, before sums are derived from a solution) -- there's
    nothing to restrict against in that case.
    """
    if run.target_sum is None:
        return None
    values = [grid[r][c] for r, c in run.cells]
    placed = frozenset(v for v in values if v is not None)
    return _candidates_for_placed(run, placed)


@lru_cache(maxsize=None)
def _candidates_for_placed(run: Run, placed: frozenset[int]) -> frozenset[int]:
    """The actual combination-filtering work behind ``run_candidate_digits``,
    split out and cached on ``(run, placed)`` -- both hashable, unlike
    ``grid`` -- since the same run/placed-digits pair is asked about
    repeatedly (once via ``solver._candidate_digits`` when a cell is
    chosen, again via ``solver._forward_check_ok`` for every sibling cell
    in the same run right after a placement, and again from the next
    search node if the just-placed cell's runs weren't fully resolved)."""
    candidates: set[int] = set()
    for combo in run_combinations(len(run.cells), run.target_sum):
        if placed <= combo:
            candidates |= combo - placed
    return frozenset(candidates)


def cell_ok(grid: Grid, cell: Cell, runs_at_cell: list[Run]) -> bool:
    """Check distinctness and (if targets are set) sum constraints for
    every run touching ``cell``. Works for both the sum-less witness-fill
    phase and the sum-aware solving phase -- see ``run_feasible``."""
    return all(distinct_in_run(grid, run) and run_feasible(grid, run) for run in runs_at_cell)


def is_complete(grid: Grid, runs: list[Run]) -> bool:
    return all(grid[r][c] is not None for run in runs for r, c in run.cells)


def is_valid_solution(grid: Grid, runs: list[Run]) -> bool:
    """Full validation of a completely filled grid against fixed clue sums."""
    if not is_complete(grid, runs):
        return False
    return all(distinct_in_run(grid, run) and run_feasible(grid, run) for run in runs)
