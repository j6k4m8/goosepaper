"""Default sizes and difficulty presets for puzzle generation."""

from __future__ import annotations

from dataclasses import dataclass

# Sizes above 20 are not supported yet. Difficulty is controlled by two
# knobs: min_blocks (region generation forces splitting until the
# partition has at least this many rectangles) and max_block_area (forces
# splitting any single region past this area regardless of min_blocks, so
# min_blocks alone can't leave one region huge while the rest split down
# small). Measured end-to-end generate_puzzle(...) time with the current
# defaults: easy/medium effectively instant (<0.05s worst case); hard
# (20x20) averages ~5s, worst case under 20s -- proving a dense Shikaku
# clue set uniquely solvable is a genuinely hard search problem
# independent of solver quality, so pushing min_blocks much higher than
# these defaults risks multi-minute generation times.
DEFAULT_SIZE = 10
SUPPORTED_SIZES = tuple(range(4, 21))


@dataclass(frozen=True)
class Difficulty:
    name: str
    # Minimum number of rectangles the grid gets split into (region
    # generation *forces* splitting until this is reached, see grid.py).
    # More, smaller rectangles = more clue numbers to reason with = harder
    # -- the actual count is often somewhat higher than this due to the
    # random continued-splitting past the minimum, for size variety.
    min_blocks: int
    # Largest area (in cells) any single rectangle may have -- region
    # generation *forces* splitting a region past this, regardless of
    # min_blocks (see grid.py: min_blocks alone doesn't stop one region
    # from staying huge while the rest split down small).
    max_block_area: int


DIFFICULTIES: dict[str, Difficulty] = {
    "easy": Difficulty("easy", min_blocks=8, max_block_area=12),
    "medium": Difficulty("medium", min_blocks=20, max_block_area=16),
    "hard": Difficulty("hard", min_blocks=20, max_block_area=36),
}

DEFAULT_DIFFICULTY = "medium"
