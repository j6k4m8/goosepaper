"""Turn a full Latin-square solution into a Futoshiki puzzle: pick a subset
of orthogonally adjacent cell pairs as inequality constraints (direction
derived from the solution), then remove numeric givens while preserving a
unique solution under the combined Latin-square + constraint rules.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .config import DEFAULT_DIFFICULTY, DIFFICULTIES, Difficulty
from .grid import generate_solution
from .rules import Cell, Constraint, Grid, index_constraints
from .solver import has_unique_solution


@dataclass
class Puzzle:
    size: int
    difficulty: str
    solution: Grid
    givens: Grid  # puzzle grid with holes (None) for the player to fill in
    constraints: list[Constraint]  # inequality signs shown on the puzzle (and honored by the solution)


def _all_adjacent_pairs(size: int) -> list[tuple[Cell, Cell]]:
    pairs: list[tuple[Cell, Cell]] = []
    for row in range(size):
        for col in range(size):
            if col + 1 < size:
                pairs.append(((row, col), (row, col + 1)))
            if row + 1 < size:
                pairs.append(((row, col), (row + 1, col)))
    return pairs


def _choose_constraints(solution: Grid, size: int, constraint_ratio: float, rng: random.Random) -> list[Constraint]:
    pairs = _all_adjacent_pairs(size)
    rng.shuffle(pairs)
    target_count = round(len(pairs) * constraint_ratio)

    constraints = []
    for cell_a, cell_b in pairs[:target_count]:
        ar, ac = cell_a
        br, bc = cell_b
        if solution[ar][ac] < solution[br][bc]:
            constraints.append(Constraint(lesser=cell_a, greater=cell_b))
        else:
            constraints.append(Constraint(lesser=cell_b, greater=cell_a))
    return constraints


def generate_puzzle(
    size: int,
    difficulty: str | Difficulty = DEFAULT_DIFFICULTY,
    rng: random.Random | None = None,
) -> Puzzle:
    """Generate a Futoshiki puzzle that has exactly one solution.

    Inequality constraints are chosen once (as a random subset of adjacent
    cell pairs, direction taken from the solution) and then held fixed;
    numeric givens are removed one at a time (in random order), keeping the
    removal only if the puzzle still solves uniquely against the fixed
    constraint set.
    """
    rng = rng or random.Random()
    diff = DIFFICULTIES[difficulty] if isinstance(difficulty, str) else difficulty

    solution = generate_solution(size, rng=rng)
    constraints = _choose_constraints(solution, size, diff.constraint_ratio, rng)
    constraints_by_cell = index_constraints(constraints)

    puzzle_grid: Grid = [row[:] for row in solution]
    positions = [(r, c) for r in range(size) for c in range(size)]
    rng.shuffle(positions)

    target_givens = round(size * size * diff.fill_ratio)
    givens_left = size * size

    for row, col in positions:
        if givens_left <= target_givens:
            break
        previous_value = puzzle_grid[row][col]
        puzzle_grid[row][col] = None
        if has_unique_solution(puzzle_grid, constraints_by_cell):
            givens_left -= 1
        else:
            puzzle_grid[row][col] = previous_value

    return Puzzle(size=size, difficulty=diff.name, solution=solution, givens=puzzle_grid, constraints=constraints)


def generate_puzzles(
    count: int,
    size: int,
    difficulty: str | Difficulty = DEFAULT_DIFFICULTY,
    rng: random.Random | None = None,
) -> list[Puzzle]:
    rng = rng or random.Random()
    return [generate_puzzle(size, difficulty, rng=rng) for _ in range(count)]
