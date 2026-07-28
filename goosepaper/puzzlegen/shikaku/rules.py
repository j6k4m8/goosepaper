"""Rule types for Shikaku: the grid must be partitioned into axis-aligned
rectangles, each containing exactly one numbered clue cell, with the
rectangle's area (width x height) equal to that number.
"""

from __future__ import annotations

from dataclasses import dataclass

Cell = tuple[int, int]


@dataclass(frozen=True)
class Rect:
    """A rectangle spanning rows ``[top, bottom)`` and columns ``[left,
    right)`` -- half-open like Python slicing, so ``area`` and adjacency
    arithmetic don't need +/-1 corrections."""

    top: int
    left: int
    bottom: int
    right: int

    @property
    def area(self) -> int:
        return (self.bottom - self.top) * (self.right - self.left)

    def contains(self, cell: Cell) -> bool:
        row, col = cell
        return self.top <= row < self.bottom and self.left <= col < self.right


def is_valid_partition(rectangles: list[Rect], size: int) -> bool:
    """True if ``rectangles`` exactly tile a size x size grid: every cell
    covered exactly once. Used as a sanity check on generated partitions
    (see grid.generate_partition, which is correct by construction, but
    this is cheap and makes that guarantee verifiable in tests)."""
    covered = [[False] * size for _ in range(size)]
    for rect in rectangles:
        for row in range(rect.top, rect.bottom):
            for col in range(rect.left, rect.right):
                if not (0 <= row < size and 0 <= col < size) or covered[row][col]:
                    return False
                covered[row][col] = True
    return all(all(row) for row in covered)
