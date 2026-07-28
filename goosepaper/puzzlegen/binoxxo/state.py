"""Incremental board state and constraint-propagation search engine.

:class:`BoardState` keeps running per-row/per-column tallies so a legality
check is O(1), and duplicate-row/-column detection is a hash-set lookup
rather than a full rescan.

``propagate()`` uses that O(1) check to repeatedly force every cell that has
exactly one legal value left (worklist/AC-3 style: after a forced placement,
only that cell's own row and column can newly become forced, so only those
get re-queued). This mirrors how real Binairo/Takuzu/0h-h1 solvers work:
propagation resolves the vast majority of cells, and backtracking
(``_explore``) is only a rarely-needed fallback for the few cells propagation
can't determine on its own.
"""

from __future__ import annotations

import random
from collections import deque

Grid = list[list[int | None]]
Cell = tuple[int, int]

# Empirically chosen: comfortably above the node count of a normal
# propagation-driven search (typically well under 1000 nodes even for
# 14x14), but low enough that a pathological blind-guess subtree gets
# aborted in well under a second instead of running for tens of seconds.
DEFAULT_NODE_BUDGET = 20_000


class BoardState:
    """Mutable, incrementally-updated view of a (partial) Binoxxo grid."""

    def __init__(self, grid: Grid):
        self.size = len(grid)
        self.half = self.size // 2
        self.grid: Grid = [row[:] for row in grid]
        self.row_counts = [[0, 0] for _ in range(self.size)]
        self.col_counts = [[0, 0] for _ in range(self.size)]
        self.row_filled = [0] * self.size
        self.col_filled = [0] * self.size
        self.complete_rows: dict[tuple[int, ...], int] = {}
        self.complete_cols: dict[tuple[int, ...], int] = {}
        self.empties: set[Cell] = set()

        for row in range(self.size):
            for col in range(self.size):
                value = self.grid[row][col]
                if value is None:
                    self.empties.add((row, col))
                else:
                    self.row_counts[row][value] += 1
                    self.col_counts[col][value] += 1
                    self.row_filled[row] += 1
                    self.col_filled[col] += 1

        for row in range(self.size):
            if self.row_filled[row] == self.size:
                key = tuple(self.grid[row])
                self.complete_rows[key] = self.complete_rows.get(key, 0) + 1
        for col in range(self.size):
            if self.col_filled[col] == self.size:
                key = tuple(self.grid[r][col] for r in range(self.size))
                self.complete_cols[key] = self.complete_cols.get(key, 0) + 1

    def is_legal(self, row: int, col: int, value: int) -> bool:
        """O(1) check: balance (via running counts) + no-triple (via the up
        to 4 immediate neighbours in each direction, not a full line scan)."""
        if self.row_counts[row][value] >= self.half:
            return False
        if self.col_counts[col][value] >= self.half:
            return False

        grid = self.grid
        size = self.size
        if col >= 2 and grid[row][col - 1] == value and grid[row][col - 2] == value:
            return False
        if 0 < col < size - 1 and grid[row][col - 1] == value and grid[row][col + 1] == value:
            return False
        if col <= size - 3 and grid[row][col + 1] == value and grid[row][col + 2] == value:
            return False
        if row >= 2 and grid[row - 1][col] == value and grid[row - 2][col] == value:
            return False
        if 0 < row < size - 1 and grid[row - 1][col] == value and grid[row + 1][col] == value:
            return False
        if row <= size - 3 and grid[row + 1][col] == value and grid[row + 2][col] == value:
            return False
        return True

    def legal_values(self, row: int, col: int) -> list[int]:
        return [value for value in (0, 1) if self.is_legal(row, col, value)]

    def place(self, row: int, col: int, value: int) -> bool:
        """Set ``(row, col)`` to ``value``.

        Returns False if this completes a row or column that duplicates an
        already-complete one elsewhere on the board. State is still updated
        consistently either way -- on False the caller must call
        ``unplace(row, col)`` to back out, same as for any other dead end.
        """
        self.grid[row][col] = value
        self.row_counts[row][value] += 1
        self.col_counts[col][value] += 1
        self.row_filled[row] += 1
        self.col_filled[col] += 1
        self.empties.discard((row, col))

        ok = True
        if self.row_filled[row] == self.size:
            key = tuple(self.grid[row])
            count = self.complete_rows.get(key, 0)
            self.complete_rows[key] = count + 1
            ok = ok and count == 0
        if self.col_filled[col] == self.size:
            key = tuple(self.grid[r][col] for r in range(self.size))
            count = self.complete_cols.get(key, 0)
            self.complete_cols[key] = count + 1
            ok = ok and count == 0
        return ok

    def unplace(self, row: int, col: int) -> None:
        value = self.grid[row][col]
        if self.row_filled[row] == self.size:
            key = tuple(self.grid[row])
            self.complete_rows[key] -= 1
            if self.complete_rows[key] == 0:
                del self.complete_rows[key]
        if self.col_filled[col] == self.size:
            key = tuple(self.grid[r][col] for r in range(self.size))
            self.complete_cols[key] -= 1
            if self.complete_cols[key] == 0:
                del self.complete_cols[key]

        self.grid[row][col] = None
        self.row_counts[row][value] -= 1
        self.col_counts[col][value] -= 1
        self.row_filled[row] -= 1
        self.col_filled[col] -= 1
        self.empties.add((row, col))


def propagate(state: BoardState, seed: list[Cell] | None = None) -> tuple[bool, list[Cell]]:
    """Force every cell that has exactly one legal value, transitively.

    ``seed`` is which empty cells to (re)check first; pass a small list (e.g.
    just the row/column of a cell that was just placed) to avoid rescanning
    the whole board -- only cells sharing a row or column with a forced cell
    can newly become forced. Defaults to every empty cell on the board,
    which is only needed once, for the initial (possibly non-empty) grid.

    Returns ``(ok, forced)``: ``forced`` are the cells this call placed (in
    placement order, for the caller to unplace again), and ``ok`` is False
    if a contradiction (a cell with zero legal values, or a forced duplicate
    row/column) was hit -- ``forced`` may be non-empty even when ok is False.
    """
    forced: list[Cell] = []
    queue: deque[Cell] = deque(seed if seed is not None else state.empties)
    queued = set(queue)

    while queue:
        row, col = queue.popleft()
        queued.discard((row, col))
        if state.grid[row][col] is not None:
            continue

        legal = state.legal_values(row, col)
        if not legal:
            return False, forced
        if len(legal) > 1:
            continue

        ok = state.place(row, col, legal[0])
        forced.append((row, col))
        if not ok:
            return False, forced

        for c in range(state.size):
            if c != col and state.grid[row][c] is None and (row, c) not in queued:
                queue.append((row, c))
                queued.add((row, c))
        for r in range(state.size):
            if r != row and state.grid[r][col] is None and (r, col) not in queued:
                queue.append((r, col))
                queued.add((r, col))

    return True, forced


def _pick_branch_cell(state: BoardState, rng: random.Random | None) -> Cell:
    if rng is not None:
        return rng.choice(tuple(state.empties))
    return next(iter(state.empties))


def _line_neighbors(state: BoardState, row: int, col: int) -> list[Cell]:
    """Empty cells sharing a row or column with ``(row, col)`` -- the only
    cells whose legality can change after that cell was just placed."""
    cells = [(row, c) for c in range(state.size) if c != col and state.grid[row][c] is None]
    cells += [(r, col) for r in range(state.size) if r != row and state.grid[r][col] is None]
    return cells


class SearchBudgetExceeded(Exception):
    """Raised when a search exceeds its node budget without resolving.

    Propagation resolves almost everything when a board already has plenty
    of givens (solving/verifying a puzzle), but building a *full* solution
    from an empty board gives propagation nothing to work with up front, so
    the first few placements are blind guesses. Most of the time that's
    still cheap, but occasionally an early guess leads deep into a dead
    subtree before a contradiction surfaces (observed: seconds instead of
    milliseconds for a small fraction of random seeds on 14x14 boards). This
    exception lets a caller bound that worst case and either retry from a
    fresh, differently-randomized attempt (see ``grid.generate_solution``,
    cheap since the common case is fast) or treat it conservatively (see
    ``solver.count_solutions``, which is never allowed to guess).
    """


def _explore(
    state: BoardState,
    on_solution,
    should_stop,
    rng: random.Random | None,
    seed: list[Cell] | None = None,
    node_budget: list[int] | None = None,
) -> None:
    """Depth-first search over completions of ``state``'s partial grid.

    Calls ``on_solution()`` for each full valid grid found (``state.grid`` is
    that solution at the time of the call -- copy it if you need to keep it,
    since the state is unwound again as the search continues/backtracks).
    Stops opening new branches once ``should_stop()`` is True. Always
    restores ``state`` to the partial assignment it had on entry before
    returning -- except when ``node_budget`` runs out, in which case this
    raises ``SearchBudgetExceeded`` and leaves ``state`` in whatever
    partially-unwound shape the exception happened to interrupt; callers
    that use a budget must treat ``state`` as unusable afterwards (a fresh
    ``BoardState`` is cheap to build, see ``count_solutions``/``find_solution``).
    """
    if node_budget is not None:
        node_budget[0] -= 1
        if node_budget[0] <= 0:
            raise SearchBudgetExceeded

    ok, forced = propagate(state, seed=seed)
    if ok:
        if not state.empties:
            on_solution()
        else:
            row, col = _pick_branch_cell(state, rng)
            legal = state.legal_values(row, col)
            if rng is not None:
                rng.shuffle(legal)
            for value in legal:
                if should_stop():
                    break
                if state.place(row, col, value):
                    _explore(
                        state,
                        on_solution,
                        should_stop,
                        rng,
                        seed=_line_neighbors(state, row, col),
                        node_budget=node_budget,
                    )
                state.unplace(row, col)

    for row, col in reversed(forced):
        state.unplace(row, col)


def count_solutions(grid: Grid, limit: int = 2, max_nodes: int | None = None) -> int:
    """Count valid completions of ``grid``, stopping early once ``limit`` is reached.

    If ``max_nodes`` is given and the search exceeds it without finishing,
    uniqueness could not be verified -- this conservatively reports ``limit``
    (i.e. "at least as many as would fail uniqueness") rather than guessing,
    since a caller like ``puzzle.generate_puzzle`` must never treat an
    unverified removal as safe.
    """
    state = BoardState(grid)
    counter = [0]
    node_budget = [max_nodes] if max_nodes is not None else None
    try:
        _explore(
            state,
            lambda: counter.__setitem__(0, counter[0] + 1),
            lambda: counter[0] >= limit,
            rng=None,
            node_budget=node_budget,
        )
    except SearchBudgetExceeded:
        return limit
    return counter[0]


def find_solution(grid: Grid, rng: random.Random | None = None, max_nodes: int | None = None) -> Grid | None:
    """Return one valid completion of ``grid``, or ``None`` if unsolvable.

    Raises ``SearchBudgetExceeded`` if ``max_nodes`` is given and exceeded
    without finding a solution -- this does *not* mean no solution exists,
    just that this attempt didn't find one within budget (see
    ``grid.generate_solution``, which retries with fresh randomness).
    """
    state = BoardState(grid)
    found: list[Grid] = []

    def on_solution() -> None:
        found.append([row[:] for row in state.grid])

    node_budget = [max_nodes] if max_nodes is not None else None
    _explore(state, on_solution, lambda: bool(found), rng=rng, node_budget=node_budget)
    return found[0] if found else None
