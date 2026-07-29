"""Default sizes and difficulty presets for puzzle generation."""

from __future__ import annotations

from dataclasses import dataclass

# Any even size >= 4 is valid (validated by module.parse_size on the CLI and
# by grid.generate_solution in the library); odd sizes can't satisfy the
# balance rule (equal number of both values per row/column).
DEFAULT_SIZE = 10


@dataclass(frozen=True)
class Difficulty:
    name: str
    # Approximate fraction of cells kept as givens (clues). Lower = harder.
    fill_ratio: float
    # Grid size used when a caller picks this difficulty without also naming an explicit
    # size - larger grids pair with harder difficulties so "hard" means more than just a
    # lower fill_ratio. Must be even (see the DEFAULT_SIZE comment above).
    size: int


DIFFICULTIES: dict[str, Difficulty] = {
    "easy": Difficulty("easy", fill_ratio=0.55, size=8),
    "medium": Difficulty("medium", fill_ratio=0.45, size=10),
    "hard": Difficulty("hard", fill_ratio=0.35, size=14),
}

DEFAULT_DIFFICULTY = "medium"

# Display symbols for the two cell values (internally always 0/1, see
# state.Grid). Index 0 is shown for value 0, index 1 for value 1. Binoxxo is
# traditionally played with "X" and "O" rather than digits.
Symbols = tuple[str, str]
DEFAULT_SYMBOLS: Symbols = ("X", "O")
