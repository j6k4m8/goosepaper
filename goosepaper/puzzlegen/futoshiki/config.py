"""Default sizes and difficulty presets for puzzle generation."""

from __future__ import annotations

from dataclasses import dataclass

# Sizes above 7 are not supported yet -- the naive backtracking uniqueness
# check in solver.py gets too slow/unreliable for larger grids (measured,
# hard difficulty, 8 seeds each: size 7 stayed under ~2.5s worst case; size 8
# ranged 1-9s and one seed didn't finish within 20s). A faster solving
# approach (constraint propagation, like binoxxo/state.py) would be needed
# before raising this -- don't just bump it without re-measuring, size 8 is
# a real cliff, not a fixed margin.
DEFAULT_SIZE = 5
SUPPORTED_SIZES = (4, 5, 6, 7)


@dataclass(frozen=True)
class Difficulty:
    name: str
    # Approximate fraction of cells kept as numeric givens. Lower = harder.
    fill_ratio: float
    # Approximate fraction of orthogonally adjacent cell pairs that get an
    # inequality sign. Lower = harder (fewer constraints to reason with).
    constraint_ratio: float
    # Grid size used when a caller picks this difficulty without also naming an explicit
    # size - larger grids pair with harder difficulties so "hard" means more than just
    # fewer givens/constraints. Must be one of SUPPORTED_SIZES.
    size: int


DIFFICULTIES: dict[str, Difficulty] = {
    "easy": Difficulty("easy", fill_ratio=0.35, constraint_ratio=0.35, size=5),
    "medium": Difficulty("medium", fill_ratio=0.20, constraint_ratio=0.25, size=6),
    "hard": Difficulty("hard", fill_ratio=0.10, constraint_ratio=0.15, size=7),
}

DEFAULT_DIFFICULTY = "medium"

# Symbols used to render cell values (0-indexed internally). Digits 1-9
# comfortably cover every supported size.
SYMBOL_ALPHABET = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
