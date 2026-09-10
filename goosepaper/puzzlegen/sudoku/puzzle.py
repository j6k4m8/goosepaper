"""Turn a full solution grid into a puzzle with a unique solution."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .config import DEFAULT_DIFFICULTY, DIFFICULTIES, Difficulty
from .grid import generate_solution
from .rules import Grid, box_size_to_n
from .solver import has_unique_solution


@dataclass
class Puzzle:
    box_size: int
    difficulty: str
    solution: Grid
    givens: Grid  # puzzle grid with holes (None) for the player to fill in

    @property
    def size(self) -> int:
        return box_size_to_n(self.box_size)


def generate_puzzle(
    box_size: int,
    difficulty: str | Difficulty = DEFAULT_DIFFICULTY,
    rng: random.Random | None = None,
) -> Puzzle:
    """Generate a Sudoku puzzle that has exactly one solution.

    Cells are removed one at a time (in random order) from a full solution,
    keeping the removal only if the puzzle still solves uniquely.
    """
    rng = rng or random.Random()
    diff = DIFFICULTIES[difficulty] if isinstance(difficulty, str) else difficulty

    solution = generate_solution(box_size, rng=rng)
    puzzle_grid: Grid = [row[:] for row in solution]

    n = box_size_to_n(box_size)
    positions = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(positions)

    target_givens = round(n * n * diff.fill_ratio)
    givens_left = n * n

    for row, col in positions:
        if givens_left <= target_givens:
            break
        previous_value = puzzle_grid[row][col]
        puzzle_grid[row][col] = None
        if has_unique_solution(puzzle_grid, box_size):
            givens_left -= 1
        else:
            puzzle_grid[row][col] = previous_value

    return Puzzle(box_size=box_size, difficulty=diff.name, solution=solution, givens=puzzle_grid)


def generate_puzzles(
    count: int,
    box_size: int,
    difficulty: str | Difficulty = DEFAULT_DIFFICULTY,
    rng: random.Random | None = None,
) -> list[Puzzle]:
    rng = rng or random.Random()
    return [generate_puzzle(box_size, difficulty, rng=rng) for _ in range(count)]
