"""Count how many solutions a (partial) Sudoku grid has.

Used by :mod:`goosepaper.puzzlegen.sudoku.puzzle` to make sure a generated
puzzle has exactly one solution before cells are removed from the full grid.
Thin wrapper -- the actual constraint-propagation search lives in
:mod:`goosepaper.puzzlegen.sudoku.state`.
"""

from __future__ import annotations

from .state import count_solutions, has_unique_solution

__all__ = ["count_solutions", "has_unique_solution"]
