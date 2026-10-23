"""Count how many rectangle partitions satisfy a Shikaku clue set.

Used by :mod:`goosepaper.puzzlegen.shikaku.puzzle` to make sure the
clue numbers (cell positions + areas) uniquely determine the rectangle
partition before a puzzle is accepted. This is an exact-cover search: place
one rectangle per clue (candidates: every axis-aligned rectangle of the
clue's area that contains its cell), backtracking on overlaps or a clue
cell claimed by another clue's rectangle.
"""

from __future__ import annotations

from functools import lru_cache

from .rules import Cell, Rect

# Bounds the worst-case search for a single count_solutions call -- large
# grids with many small clues (see grid.py's min_blocks-driven generation)
# can occasionally produce a genuinely hard-to-solve clue set (observed:
# some 20x20/~100-clue instances still exceed 500,000 nodes and multiple
# seconds even with cached candidates, other-clue-exclusion precomputed
# once, and incremental candidate narrowing). Rather than let one
# pathological instance block generation indefinitely, cap the search and
# let the caller (puzzle.py) treat "budget exceeded" the same as "not
# proven unique" and try a fresh partition instead -- the same
# conservative pattern used in Binoxxo's and Kakuro's solvers.
DEFAULT_NODE_BUDGET = 500_000


class SearchBudgetExceeded(Exception):
    """Raised when a search exceeds its node budget without resolving."""


@lru_cache(maxsize=None)
def _candidate_rects(cell: Cell, area: int, size: int) -> tuple[Rect, ...]:
    """Every axis-aligned rectangle of the given area that contains
    ``cell`` and fits within a size x size grid.

    A clue's ``(cell, area, size)`` never changes during a search, so this
    was being rebuilt from scratch at every single node for no reason --
    cached, since the same handful of clues get asked for repeatedly
    across possibly many thousands of nodes."""
    row, col = cell
    candidates: list[Rect] = []
    for height in range(1, area + 1):
        if area % height != 0:
            continue
        width = area // height
        if width > size or height > size:
            continue
        for top in range(max(0, row - height + 1), min(row, size - height) + 1):
            for left in range(max(0, col - width + 1), min(col, size - width) + 1):
                candidates.append(Rect(top, left, top + height, left + width))
    return tuple(candidates)


def _rects_overlap(a: Rect, b: Rect) -> bool:
    """O(1) axis-aligned rectangle intersection test -- used instead of
    iterating every cell of a candidate against a ``covered`` grid, which
    is what made this solver too slow to scale past ~10x10 grids with
    dozens of clues."""
    return not (a.right <= b.left or b.right <= a.left or a.bottom <= b.top or b.bottom <= a.top)


def _bounding_box(rects: list[Rect]) -> tuple[int, int, int, int]:
    return (
        min(r.top for r in rects),
        min(r.left for r in rects),
        max(r.bottom for r in rects),
        max(r.right for r in rects),
    )


def _bbox_overlaps_rect(box: tuple[int, int, int, int], rect: Rect) -> bool:
    top, left, bottom, right = box
    return not (right <= rect.left or rect.right <= left or bottom <= rect.top or rect.bottom <= top)


def count_solutions(size: int, clues: dict[Cell, int], limit: int = 2, max_nodes: int | None = DEFAULT_NODE_BUDGET) -> int:
    """Count full tilings (every clue covered by exactly one rectangle of
    its area, every cell covered exactly once), stopping early once
    ``limit`` is reached.

    Two things make this tractable well beyond the smallest grids:

    1. Each clue's candidates are filtered against every *other* clue's
       cell exactly once up front, before any recursion -- clue positions
       never change during a search, so re-checking "does this candidate
       contain a different clue's cell" at every node (the original
       approach) was pure waste.
    2. Candidates are narrowed *incrementally*: placing a rectangle
       removes it and any now-overlapping candidate from every other
       remaining clue's live candidate list (via a cheap O(1)
       rectangle-vs-rectangle test, not an O(area) cell-by-cell scan
       against a shared "covered" grid), with an undo log so backtracking
       restores exactly what changed. A per-clue candidate bounding box is
       kept alongside so a clue whose candidates couldn't possibly
       overlap the just-placed rectangle is skipped in O(1) rather than
       re-filtered.

    At every node, the next clue to branch on is still the one with the
    fewest live candidates (dynamic most-constrained-variable choice, the
    standard ordering heuristic for exact-cover search, e.g. Knuth's
    Dancing Links).

    Even with all of that, some instances (observed: dense clue sets on
    large grids) remain genuinely hard to prove unique. If ``max_nodes``
    is given and the search doesn't finish within it, raises
    ``SearchBudgetExceeded`` -- callers that can't afford to block
    indefinitely should catch this and treat the result as unresolved.
    """
    clue_cells = set(clues)
    live: dict[Cell, list[Rect]] = {}
    boxes: dict[Cell, tuple[int, int, int, int] | None] = {}
    for cell, area in clues.items():
        others = clue_cells - {cell}
        candidates = [rect for rect in _candidate_rects(cell, area, size) if not any(rect.contains(o) for o in others)]
        live[cell] = candidates
        boxes[cell] = _bounding_box(candidates) if candidates else None

    node_budget = [max_nodes] if max_nodes is not None else None
    return _count(frozenset(clues), live, boxes, limit, node_budget, 0, size * size)


def _count(
    remaining: frozenset[Cell],
    live: dict[Cell, list[Rect]],
    boxes: dict[Cell, tuple[int, int, int, int] | None],
    limit: int,
    node_budget: list[int] | None,
    covered_area: int,
    total_area: int,
) -> int:
    if node_budget is not None:
        node_budget[0] -= 1
        if node_budget[0] <= 0:
            raise SearchBudgetExceeded

    if not remaining:
        # All clues placed without conflict -- but that alone doesn't mean
        # the grid is fully tiled (e.g. clue areas not summing to
        # size*size would leave gaps while every individual placement
        # still looked valid, most simply: no clues at all on a non-empty
        # grid). Tracking the running covered area alongside the search
        # (instead of a full "covered" cell grid, which is what this
        # solver used to check this with) is how the O(1) rectangle-vs-
        # rectangle overlap tests below stay O(1) -- no per-cell grid to
        # rescan at the end either.
        return 1 if covered_area == total_area else 0

    best_cell = min(remaining, key=lambda cell: len(live[cell]))
    candidates = live[best_cell]
    if not candidates:
        return 0

    rest = remaining - {best_cell}
    found = 0
    for rect in candidates:
        changed = _narrow_candidates(rect, rest, live, boxes)
        found += _count(rest, live, boxes, limit, node_budget, covered_area + rect.area, total_area)
        _restore_candidates(changed, live, boxes)
        if found >= limit:
            return found
    return found


def _narrow_candidates(
    placed: Rect,
    cells: frozenset[Cell],
    live: dict[Cell, list[Rect]],
    boxes: dict[Cell, tuple[int, int, int, int] | None],
) -> list[tuple[Cell, list[Rect], tuple[int, int, int, int] | None]]:
    """Remove any candidate overlapping ``placed`` from every cell in
    ``cells``' live lists, skipping a cell entirely (O(1)) when its
    candidates' bounding box can't possibly overlap ``placed``. Returns
    the (cell, old_candidates, old_box) triples actually changed, for
    ``_restore_candidates`` to undo."""
    changed = []
    for cell in cells:
        box = boxes[cell]
        if box is None or not _bbox_overlaps_rect(box, placed):
            continue
        old_candidates = live[cell]
        new_candidates = [rect for rect in old_candidates if not _rects_overlap(rect, placed)]
        if len(new_candidates) != len(old_candidates):
            changed.append((cell, old_candidates, box))
            live[cell] = new_candidates
            boxes[cell] = _bounding_box(new_candidates) if new_candidates else None
    return changed


def _restore_candidates(
    changed: list[tuple[Cell, list[Rect], tuple[int, int, int, int] | None]],
    live: dict[Cell, list[Rect]],
    boxes: dict[Cell, tuple[int, int, int, int] | None],
) -> None:
    for cell, old_candidates, old_box in changed:
        live[cell] = old_candidates
        boxes[cell] = old_box


def has_unique_solution(size: int, clues: dict[Cell, int]) -> bool:
    return count_solutions(size, clues, limit=2) == 1
