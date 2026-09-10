"""Incremental board state and constraint-propagation search engine.

Bitmask candidate sets updated incrementally (diff-based place/unplace, no
full grid rescans) plus a ``propagate()`` step applied before every
branching decision, so backtracking only has to resolve the small residue
propagation can't determine on its own. The two propagation rules are the
standard human Sudoku-solving techniques:

- **Naked single**: a cell with exactly one remaining candidate must be
  that value.
- **Hidden single**: a value that fits in only one cell of some row,
  column, or box must go there, even if that cell still has other
  candidates too.

Naive backtracking (re-validating whole rows/columns/boxes from scratch
after every trial placement, no candidate information at all) is fine for
filling a fresh, unconstrained grid, but explosively slow for uniqueness
checks against a near-empty "hard" grid. Naked/hidden singles alone resolve
the overwhelming majority of cells in a randomly generated puzzle; only a
small residue -- often none at all -- needs actual search.
"""

from __future__ import annotations

from functools import lru_cache

from .rules import Grid, box_size_to_n

Cell = tuple[int, int]


@lru_cache(maxsize=None)
def _units_for(box_size: int) -> tuple[tuple[Cell, ...], ...]:
    """Every row, column, and box as a tuple of cells. Depends only on
    ``box_size``, so cached across calls (only a couple of distinct
    values are ever used)."""
    n = box_size_to_n(box_size)
    units: list[tuple[Cell, ...]] = []
    for r in range(n):
        units.append(tuple((r, c) for c in range(n)))
    for c in range(n):
        units.append(tuple((r, c) for r in range(n)))
    for box_row in range(0, n, box_size):
        for box_col in range(0, n, box_size):
            units.append(
                tuple((box_row + dr, box_col + dc) for dr in range(box_size) for dc in range(box_size))
            )
    return tuple(units)


@lru_cache(maxsize=None)
def _peers_for(box_size: int) -> dict[Cell, tuple[Cell, ...]]:
    """For every cell, every other cell sharing its row, column, or box."""
    n = box_size_to_n(box_size)
    peers: dict[Cell, set[Cell]] = {(r, c): set() for r in range(n) for c in range(n)}
    for unit in _units_for(box_size):
        for cell in unit:
            peers[cell].update(other for other in unit if other != cell)
    return {cell: tuple(sorted(others)) for cell, others in peers.items()}


class SudokuState:
    """Mutable, incrementally-updated view of a (partial) Sudoku grid."""

    def __init__(self, grid: Grid, box_size: int):
        self.box_size = box_size
        self.size = box_size_to_n(box_size)
        self.grid: Grid = [row[:] for row in grid]
        self.units = _units_for(box_size)
        self.peers = _peers_for(box_size)
        self.empties: set[Cell] = {
            (r, c) for r in range(self.size) for c in range(self.size) if self.grid[r][c] is None
        }

        full_mask = (1 << self.size) - 1
        self.candidates: list[list[int]] = [[full_mask] * self.size for _ in range(self.size)]
        for r in range(self.size):
            for c in range(self.size):
                value = self.grid[r][c]
                if value is not None:
                    for pr, pc in self.peers[(r, c)]:
                        self.candidates[pr][pc] &= ~(1 << value)

    def place(self, row: int, col: int, value: int) -> list[Cell]:
        """Assign ``grid[row][col] = value`` and eliminate ``value`` from
        every still-empty peer's candidates. Returns the peers whose
        candidates actually changed (i.e. that still had ``value`` as a
        candidate) -- pass this list to :meth:`unplace` to precisely
        reverse the elimination. A peer already excluding ``value``
        (because some *other* placement excluded it first) is not
        included, and must not be included: blindly restoring the bit on
        every unplace would re-admit a value a still-active placement
        continues to forbid.
        """
        self.grid[row][col] = value
        self.empties.discard((row, col))
        bit = 1 << value
        changed: list[Cell] = []
        for pr, pc in self.peers[(row, col)]:
            if (pr, pc) in self.empties and self.candidates[pr][pc] & bit:
                self.candidates[pr][pc] &= ~bit
                changed.append((pr, pc))
        return changed

    def unplace(self, row: int, col: int, changed: list[Cell]) -> None:
        bit = 1 << self.grid[row][col]
        for pr, pc in changed:
            self.candidates[pr][pc] |= bit
        self.grid[row][col] = None
        self.empties.add((row, col))

    def propagate(self) -> tuple[bool, list[tuple[Cell, list[Cell]]]]:
        """Repeatedly force naked singles and hidden singles until a
        fixpoint or a contradiction (a cell or a unit-value with zero
        candidates). Returns ``(ok, forced)``, where ``forced`` is every
        placement this call made, in order -- the caller must unplace
        them (in reverse) regardless of ``ok``, since a contradiction can
        be discovered after some placements already happened.
        """
        forced: list[tuple[Cell, list[Cell]]] = []

        while True:
            progressed = False

            for row, col in list(self.empties):
                mask = self.candidates[row][col]
                if mask == 0:
                    return False, forced
                if mask & (mask - 1) == 0:
                    value = mask.bit_length() - 1
                    changed = self.place(row, col, value)
                    forced.append(((row, col), changed))
                    progressed = True

            if not self.empties:
                return True, forced

            for unit in self.units:
                values_present = 0
                for row, col in unit:
                    value = self.grid[row][col]
                    if value is not None:
                        values_present |= 1 << value

                counts = [0] * self.size
                last_cell: list[Cell | None] = [None] * self.size
                for row, col in unit:
                    if self.grid[row][col] is not None:
                        continue
                    remaining = self.candidates[row][col]
                    while remaining:
                        low_bit = remaining & (-remaining)
                        value = low_bit.bit_length() - 1
                        counts[value] += 1
                        last_cell[value] = (row, col)
                        remaining &= remaining - 1

                for value in range(self.size):
                    if values_present & (1 << value):
                        continue
                    if counts[value] == 0:
                        return False, forced
                    if counts[value] == 1:
                        row, col = last_cell[value]
                        if self.grid[row][col] is None:
                            changed = self.place(row, col, value)
                            forced.append(((row, col), changed))
                            progressed = True

            if not progressed:
                return True, forced


def _pick_branch_cell(state: SudokuState) -> Cell:
    """Most-constrained-variable heuristic: the empty cell with the fewest
    remaining candidates. Every remaining empty cell has at least 2
    candidates at this point (fewer would already have been forced by
    ``propagate``), so this is the branch most likely to fail fast."""
    best_cell: Cell | None = None
    best_count = None
    for row, col in state.empties:
        count = bin(state.candidates[row][col]).count("1")
        if best_count is None or count < best_count:
            best_cell, best_count = (row, col), count
            if count <= 2:
                break
    assert best_cell is not None
    return best_cell


def _candidate_values(mask: int) -> list[int]:
    values = []
    while mask:
        low_bit = mask & (-mask)
        values.append(low_bit.bit_length() - 1)
        mask &= mask - 1
    return values


def _explore(state: SudokuState, on_solution, should_stop) -> None:
    """Depth-first search over completions of ``state``'s partial grid,
    with ``propagate()`` applied before every branch. Calls
    ``on_solution()`` for each full valid grid found and stops opening new
    branches once ``should_stop()`` is True. Always restores ``state`` to
    the partial assignment it had on entry before returning."""
    ok, forced = state.propagate()
    if ok:
        if not state.empties:
            on_solution()
        else:
            row, col = _pick_branch_cell(state)
            for value in _candidate_values(state.candidates[row][col]):
                if should_stop():
                    break
                changed = state.place(row, col, value)
                _explore(state, on_solution, should_stop)
                state.unplace(row, col, changed)

    for (row, col), changed in reversed(forced):
        state.unplace(row, col, changed)


def count_solutions(grid: Grid, box_size: int, limit: int = 2) -> int:
    """Count valid completions of ``grid``, stopping early once ``limit``
    is reached. ``grid`` is not modified."""
    state = SudokuState(grid, box_size)
    counter = [0]
    _explore(state, lambda: counter.__setitem__(0, counter[0] + 1), lambda: counter[0] >= limit)
    return counter[0]


def has_unique_solution(grid: Grid, box_size: int) -> bool:
    return count_solutions(grid, box_size, limit=2) == 1
