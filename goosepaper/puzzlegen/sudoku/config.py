"""Default sizes and difficulty presets for puzzle generation."""

from __future__ import annotations

from dataclasses import dataclass

# box_size 3 = classic 9x9 Sudoku (3x3 boxes), 2 = 4x4 (quick/easy variant).
#
# box_size 4 (16x16) is not supported: at that size and "hard" difficulty's
# low given-count, naked/hidden singles alone (see state.py) no longer keep
# backtracking small enough to be reliably fast. Callers must validate
# box_size themselves.
DEFAULT_BOX_SIZE = 3
SUPPORTED_BOX_SIZES = (2, 3)


@dataclass(frozen=True)
class Difficulty:
    name: str
    # Approximate fraction of cells kept as givens (clues). Lower = harder.
    fill_ratio: float


DIFFICULTIES: dict[str, Difficulty] = {
    "easy": Difficulty("easy", 0.55),
    "medium": Difficulty("medium", 0.40),
    "hard": Difficulty("hard", 0.30),
}

DEFAULT_DIFFICULTY = "medium"

# Symbols used to render cell values (0-indexed internally). Digits 1-9 for
# the classic case, extended with letters for box sizes above 3 (16x16 etc.).
SYMBOL_ALPHABET = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
