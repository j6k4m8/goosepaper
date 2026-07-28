"""Default sizes and difficulty presets for puzzle generation."""

from __future__ import annotations

from dataclasses import dataclass

# Sizes above 7 are not supported yet. Kakuro has no numeric givens to
# bootstrap the search from (unlike Sudoku/Futoshiki), so verifying
# uniqueness is a much harder backtracking problem for the same grid size.
# 6-7 only became practical after two changes:
#   1. solver.py restricts candidate digits per cell using precomputed
#      per-run combination tables (rules.run_combinations) instead of
#      trying 1-9 and pruning after the fact, plus forward-checking after
#      every placement -- the standard real-world Kakuro solving
#      technique, not just min/max bound pruning.
#   2. grid.py caps every run (horizontal by construction, vertical via a
#      single safe-cut repair pass) at MAX_RUN_LENGTH_AFTER_SPLIT cells --
#      row-independent pattern composition left vertical run length
#      completely uncontrolled, and 6x6/7x7 layouts with a dozen
#      length-6/7 runs were common, not rare, at the black ratios that
#      still look "hard".
# Even with both fixes, larger sizes/harder difficulties get noticeably
# slower, never hang (measured 12 seeds each, 25s bound):
#   6x6 medium: 12/12 finished, avg 3.6s, worst 13.4s.
#   6x6 hard:   11/12 finished (1 safely raised RuntimeError, not a hang),
#               avg 3.0s, worst 12.5s.
#   7x7 medium: 11/12 finished within 25s, avg 5.3s, worst 19.2s.
#   7x7 hard:   9/12 finished within 25s (3 exceeded it), avg (of the ones
#               that finished) 9.6s, worst 23.9s -- the genuine slow tail.
# 7x7/hard is usable but the one combination where an occasional generate
# call can take 20-30s. Revisit past 7 only after profiling that specific
# size again, not by extrapolation.
DEFAULT_SIZE = 4
SUPPORTED_SIZES = (4, 5, 6, 7)


@dataclass(frozen=True)
class Difficulty:
    name: str
    # Fraction of interior cells that start black. Higher = shorter runs =
    # easier (Kakuro has no numeric givens to remove -- unlike the other
    # modules, difficulty comes entirely from the black/white pattern).
    black_ratio: float


DIFFICULTIES: dict[str, Difficulty] = {
    "easy": Difficulty("easy", black_ratio=0.35),
    "medium": Difficulty("medium", black_ratio=0.25),
    "hard": Difficulty("hard", black_ratio=0.18),
}

DEFAULT_DIFFICULTY = "medium"
