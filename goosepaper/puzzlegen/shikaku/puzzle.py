"""Turn a rectangle partition into a Shikaku puzzle: pick one clue cell per
rectangle (value = its area) and verify the resulting clue set uniquely
determines the partition.

Unlike the other modules there's no separate "givens removal" step: every
rectangle contributes exactly one clue by definition of the puzzle, and
that's always shown -- difficulty comes entirely from the partition itself
(``Difficulty.min_blocks``, see config.py), not from hiding cells.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .config import DEFAULT_DIFFICULTY, DIFFICULTIES, Difficulty
from .grid import generate_partition
from .rules import Cell, Rect
from .solver import SearchBudgetExceeded, has_unique_solution

MAX_PARTITION_ATTEMPTS = 300


@dataclass
class Puzzle:
    size: int
    difficulty: str
    clues: dict[Cell, int]
    rectangles: list[Rect]  # the solution's partition


def _unique(size: int, clues: dict[Cell, int]) -> bool:
    """``has_unique_solution`` treating an unresolved (budget-exceeded)
    search the same as "not proven unique yet" -- some clue sets (dense,
    large grids especially) have a branching factor too large to fully
    explore, and it's both cheaper and safer to try a fresh partition than
    to trust an unverified result (same conservative stance as Kakuro's
    ``puzzle._unique``)."""
    try:
        return has_unique_solution(size, clues)
    except SearchBudgetExceeded:
        return False


def generate_puzzle(
    size: int,
    difficulty: str | Difficulty = DEFAULT_DIFFICULTY,
    min_blocks: int | None = None,
    max_block_area: int | None = None,
    rng: random.Random | None = None,
) -> Puzzle:
    """Generate a Shikaku puzzle that has exactly one solution.

    A rectangle partition is generated (always valid by construction, see
    ``grid.generate_partition``), one clue cell is chosen per rectangle,
    and the whole clue set is checked for uniqueness; if the same numbers
    could also be tiled a different way (or uniqueness couldn't be proven
    within the solver's node budget), a fresh partition is tried.

    ``min_blocks``/``max_block_area`` override the difficulty preset's own
    values (``Difficulty.min_blocks``/``Difficulty.max_block_area``) when
    given -- lets a caller (the CLI's ``--min-blocks``/``--max-block-size``)
    ask for specific values independent of difficulty.
    """
    rng = rng or random.Random()
    diff = DIFFICULTIES[difficulty] if isinstance(difficulty, str) else difficulty
    effective_min_blocks = diff.min_blocks if min_blocks is None else min_blocks
    effective_max_block_area = diff.max_block_area if max_block_area is None else max_block_area

    for _ in range(MAX_PARTITION_ATTEMPTS):
        rectangles = generate_partition(size, rng, effective_min_blocks, effective_max_block_area)
        clues: dict[Cell, int] = {}
        for rect in rectangles:
            row = rng.randint(rect.top, rect.bottom - 1)
            col = rng.randint(rect.left, rect.right - 1)
            clues[(row, col)] = rect.area

        if _unique(size, clues):
            return Puzzle(size=size, difficulty=diff.name, clues=clues, rectangles=rectangles)

    raise RuntimeError(f"could not generate a unique {size}x{size} Shikaku puzzle")


def generate_puzzles(
    count: int,
    size: int,
    difficulty: str | Difficulty = DEFAULT_DIFFICULTY,
    min_blocks: int | None = None,
    max_block_area: int | None = None,
    rng: random.Random | None = None,
) -> list[Puzzle]:
    rng = rng or random.Random()
    return [
        generate_puzzle(size, difficulty, min_blocks=min_blocks, max_block_area=max_block_area, rng=rng)
        for _ in range(count)
    ]
