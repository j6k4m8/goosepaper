"""Generation of Kakuro layouts (black/white pattern + runs) and a witness
digit fill.

Unlike the other modules there are two independent generation phases here:
the black/white *pattern* (this file, ``generate_layout``) and the digit
*fill* that turns a pattern into an actual solution (this file,
``fill_values``) -- clue sums only exist once a fill is chosen and get
derived from it afterwards, see ``puzzle.py``.
"""

from __future__ import annotations

import random

from .rules import Cell, Grid, Run, canvas_size, cell_ok, compute_runs, has_invalid_run_length, ordered_cells, runs_by_cell

# Each attempt is sub-millisecond (see AGENTS.md for measured numbers), so
# a generous budget costs little even when a lot of attempts are needed --
# raised from 500 to 5000 once MAX_RUN_LENGTH_AFTER_SPLIT (below) made
# valid-and-capped patterns rarer at size 7 (~1 in 5-6 attempts, vs ~1 in 8
# for the original uncapped size-6 case the smaller budget was tuned for).
MAX_LAYOUT_ATTEMPTS = 5000
# Sanity floor so an unlucky pattern isn't accepted with barely any
# playable cells at all.
MIN_WHITE_FRACTION = 0.35

# Runs longer than this drove count_solutions into minutes-long searches
# even with combination-table pruning and forward-checking (see AGENTS.md
# for measured numbers). Horizontal runs are composed as atomic units (see
# _compose_row), so this is enforced there directly by never choosing a
# longer length in the first place -- the digit-validity ceiling of 9 is
# still what has_invalid_run_length checks, this is a stricter,
# computational-tractability ceiling on top of it. Vertical runs get no
# such treatment from row-by-row composition (an emergent side effect of
# how independently-chosen rows happen to stack), so they need a separate
# repair pass -- see _split_long_vertical_runs. 6 (not 5) is the smallest
# value that still lets size-7 layouts succeed reliably within
# MAX_LAYOUT_ATTEMPTS -- see AGENTS.md for the measurement.
MAX_RUN_LENGTH_AFTER_SPLIT = 6


def generate_layout(size: int, black_ratio: float, rng: random.Random) -> tuple[list[list[bool]], list[Run]]:
    """Generate a black/white pattern where every run (horizontal and
    vertical) has a valid length (2-9, since digits 1-9 must be distinct
    within a run) and none exceeds ``MAX_RUN_LENGTH_AFTER_SPLIT`` cells.

    Each row is composed independently so that *horizontal* runs are valid
    by construction (white-run segments are always length 0 or 2-9, never
    1 -- see ``_compose_row``); this alone leaves *vertical* runs
    uncontrolled (an emergent side effect of how independently-chosen rows
    happen to stack), and at black ratios low enough to still look "hard",
    columns routinely run white almost top to bottom (observed: 7x7/hard
    layouts with a dozen length-7 runs are common, not rare, and drove
    uniqueness-checking into minutes-long searches even with combination-
    table pruning and forward-checking in solver.py -- see AGENTS.md).

    ``_split_long_vertical_runs`` repairs that in a single pass (never
    iterated -- an earlier version tried iteratively patching individual
    bad runs by blackening cells, which could fix one run while breaking
    another and cascade into blackening almost the whole grid). If the
    single-pass repair itself produces an invalid or still-too-long run
    (splitting a vertical run can clip a horizontal one at the same cell),
    the whole pattern -- composition and repair both -- is discarded and a
    fresh one is composed from scratch, same as any other invalid
    candidate.
    """
    n = canvas_size(size)

    for _ in range(MAX_LAYOUT_ATTEMPTS):
        black = _random_pattern(n, black_ratio, rng)
        black = _split_long_vertical_runs(black, n)
        runs = compute_runs(black)
        white_count = sum(not cell for row in black for cell in row)
        if (
            not has_invalid_run_length(runs)
            and not any(len(run.cells) > MAX_RUN_LENGTH_AFTER_SPLIT for run in runs)
            and white_count >= MIN_WHITE_FRACTION * size * size
        ):
            return black, runs

    raise RuntimeError(f"could not generate a valid {size}x{size} Kakuro layout after {MAX_LAYOUT_ATTEMPTS} attempts")


def _split_long_vertical_runs(black: list[list[bool]], n: int) -> list[list[bool]]:
    """Single repair pass: blacken one cell inside every vertical run
    longer than ``MAX_RUN_LENGTH_AFTER_SPLIT``, bisecting it so both
    pieces end up in ``[2, MAX_RUN_LENGTH_AFTER_SPLIT]`` cells. One cut
    always suffices: a Kakuro run can never exceed 9 cells (digits 1-9
    must be distinct), and with ``MAX_RUN_LENGTH_AFTER_SPLIT = 6`` every
    length from 2-9 has a cut point leaving both sides <= 6, so no
    recursive re-splitting is ever needed.

    Naively bisecting at the midpoint corrupted the *horizontal* run
    passing through the cut cell far more often than not (splitting it
    into a 1-cell fragment on one side) -- ``_find_safe_cut`` only ever
    picks a row where blackening ``(row, col)`` leaves that horizontal run
    at 0 or >= 2 cells on both sides, checked against the grid's *current*
    state (including any earlier cuts already made in this same pass, not
    just the original pattern) so cuts landing in the same row never
    interact badly with each other either. If no candidate row in a run's
    valid cut range is horizontally safe, that run is left too long --
    ``generate_layout``'s own re-check then rejects the whole pattern and
    a fresh one is composed, rather than risking a corrupt result.
    """
    black = [row[:] for row in black]
    for col in range(1, n):
        run_start = None
        for row in range(1, n + 1):
            is_white = row < n and not black[row][col]
            if is_white and run_start is None:
                run_start = row
            elif not is_white and run_start is not None:
                _bisect_vertical_run(black, n, col, run_start, row)
                run_start = None
    return black


def _bisect_vertical_run(black: list[list[bool]], n: int, col: int, start: int, end: int) -> None:
    if end - start <= MAX_RUN_LENGTH_AFTER_SPLIT:
        return
    cut = _find_safe_cut(black, n, col, start, end)
    if cut is not None:
        black[cut][col] = True
    # else: left too long on purpose -- see _split_long_vertical_runs


def _find_safe_cut(black: list[list[bool]], n: int, col: int, start: int, end: int) -> int | None:
    """A row in ``[start, end)`` where blackening ``(row, col)`` leaves
    both the vertical pieces (``[start, row)``/``[row + 1, end)``) at
    ``[2, MAX_RUN_LENGTH_AFTER_SPLIT]`` cells and the horizontal run
    through ``(row, col)`` at 0 or >= 2 cells. Prefers rows closest to the
    midpoint among the safe ones. ``None`` if no row in range is
    horizontally safe."""
    lo = max(start + 2, end - 1 - MAX_RUN_LENGTH_AFTER_SPLIT)
    hi = min(start - 1 + MAX_RUN_LENGTH_AFTER_SPLIT, end - 3)
    mid = (start + end) // 2
    for row in sorted(range(lo, hi + 1), key=lambda r: abs(r - mid)):
        if _horizontal_split_ok(black, n, row, col):
            return row
    return None


def _horizontal_split_ok(black: list[list[bool]], n: int, row: int, col: int) -> bool:
    h_start = col
    while h_start > 0 and not black[row][h_start - 1]:
        h_start -= 1
    h_end = col + 1
    while h_end < n and not black[row][h_end]:
        h_end += 1
    left_len = col - h_start
    right_len = h_end - col - 1
    return (left_len == 0 or left_len >= 2) and (right_len == 0 or right_len >= 2)


def _random_pattern(n: int, black_ratio: float, rng: random.Random) -> list[list[bool]]:
    """Row 0 (and column 0 of every row) stays black -- the clue border."""
    black = [[True] * n]
    for _ in range(1, n):
        black.append(_compose_row(n, black_ratio, rng))
    return black


def _compose_row(n: int, black_ratio: float, rng: random.Random) -> list[bool]:
    """One row, built left to right as alternating black gaps and white
    runs. White runs are only ever started with length 2 up to
    ``MAX_RUN_LENGTH_AFTER_SPLIT`` (never 1, and never longer than the
    cap), so a row built this way can never contain an invalid *or*
    too-long horizontal run -- no separate horizontal repair pass is
    needed, unlike vertical runs (see ``_split_long_vertical_runs``)."""
    row = [True]  # column 0 border
    col = 1
    while col < n:
        remaining = n - col
        if remaining > 1 and rng.random() >= black_ratio:
            run_len = _random_run_length(min(MAX_RUN_LENGTH_AFTER_SPLIT, remaining), rng)
            row.extend([False] * run_len)
            col += run_len
        else:
            row.append(True)
            col += 1
    return row


# Weighted toward short runs: a uniform choice over 2..9 makes long runs
# (5+ cells) far too common, which blows up the solving/uniqueness-checking
# branching factor -- a 6x6 grid with several 6-cell runs can take seconds
# to tens of seconds to verify, and real published Kakuro puzzles are
# mostly 2-4 cell runs with long runs as the exception, not the rule.
_RUN_LENGTH_WEIGHTS = {2: 30, 3: 25, 4: 18, 5: 12, 6: 8, 7: 4, 8: 2, 9: 1}


def _random_run_length(max_len: int, rng: random.Random) -> int:
    lengths = list(range(2, max_len + 1))
    weights = [_RUN_LENGTH_WEIGHTS[length] for length in lengths]
    return rng.choices(lengths, weights=weights, k=1)[0]


def fill_values(runs: list[Run], n: int, rng: random.Random) -> Grid:
    """Fill every white cell with a digit 1-9, distinct within each run
    (horizontal and vertical) it belongs to. No sum target is enforced yet
    -- ``runs`` here must have ``target_sum is None`` (fresh from
    ``compute_runs``); sums get derived from the result afterwards."""
    grid: Grid = [[None] * n for _ in range(n)]
    cells = ordered_cells(runs)
    index = runs_by_cell(runs)

    if not _fill(grid, 0, cells, index, rng):
        raise RuntimeError("could not fill a valid Kakuro digit assignment")
    return grid


def _fill(grid: Grid, idx: int, cells: list[Cell], index: dict[Cell, list[Run]], rng: random.Random) -> bool:
    if idx == len(cells):
        return True

    row, col = cells[idx]
    values = list(range(1, 10))
    rng.shuffle(values)

    for value in values:
        grid[row][col] = value
        if cell_ok(grid, (row, col), index.get((row, col), [])):
            if _fill(grid, idx + 1, cells, index, rng):
                return True
        grid[row][col] = None

    return False
