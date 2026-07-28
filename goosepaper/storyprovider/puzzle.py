"""Logic puzzles (Sudoku, Binoxxo, Futoshiki, Kakuro, Shikaku) rendered as plain HTML - tables,
inline CSS, nothing else.

Generation lives in :mod:`goosepaper.puzzlegen` - vendored, dependency-free grid/solver code with
no rendering of its own, one subpackage per puzzle type. This module owns all rendering. No image
rasterization, no reportlab, nothing beyond what WeasyPrint (goosepaper's existing HTML-to-PDF
renderer) already handles.
"""

from __future__ import annotations

import random
from typing import Callable, Dict, List, Optional, Tuple

from ..puzzlegen import binoxxo, futoshiki, kakuro, shikaku, sudoku
from ..story import Story
from ..util import PlacementPreference
from .storyprovider import StoryProvider

_PUZZLE_CSS = """
<style>
table.puzzle-grid, table.futoshiki-grid, table.kakuro-grid, table.shikaku-grid {
  border-collapse: collapse; margin: 0 auto 1em auto; page-break-inside: avoid;
}
table.puzzle-grid td { width: 2em; height: 2em; text-align: center; vertical-align: middle;
  font-family: monospace; font-size: 1.15em; border: 1px solid #999; padding: 0; }
table.puzzle-grid tr:first-child td { border-top: 2px solid #000; }
table.puzzle-grid td:first-child { border-left: 2px solid #000; }
table.puzzle-grid td.box-left { border-left: 2px solid #000; }
table.puzzle-grid tr.box-top td { border-top: 2px solid #000; }
table.puzzle-grid tr:last-child td { border-bottom: 2px solid #000; }
table.puzzle-grid td:last-child { border-right: 2px solid #000; }

table.futoshiki-grid td.fut-cell { width: 1.8em; height: 1.8em; text-align: center;
  vertical-align: middle; font-family: monospace; font-size: 1.1em; border: 1px solid #999; }
table.futoshiki-grid td.fut-hgap { width: 0.7em; text-align: center; vertical-align: middle;
  font-weight: bold; }
table.futoshiki-grid td.fut-vgap { height: 0.7em; text-align: center; vertical-align: middle;
  font-weight: bold; font-size: 0.85em; }
table.futoshiki-grid td.fut-spacer { width: 0.7em; height: 0.7em; }

table.kakuro-grid td { width: 2em; height: 2em; border: 1px solid #999; padding: 0;
  text-align: center; font-family: monospace; }
table.kakuro-grid td.kakuro-black {
  background: linear-gradient(to top right, #000 49.5%, #999 49.5%, #999 50.5%, #000 50.5%);
  position: relative;
}
table.kakuro-grid .kakuro-clue { position: relative; width: 100%; height: 100%; }
table.kakuro-grid .kakuro-h { position: absolute; top: 0; right: 2px; font-size: 0.5em; color: #fff; }
table.kakuro-grid .kakuro-v { position: absolute; bottom: 0; left: 2px; font-size: 0.5em; color: #fff; }

table.shikaku-grid td { width: 1.7em; height: 1.7em; text-align: center; vertical-align: middle;
  font-family: monospace; font-size: 0.9em; border: 1px solid #ccc; }
table.shikaku-grid td.shikaku-left { border-left: 2px solid #000; }
table.shikaku-grid td.shikaku-right { border-right: 2px solid #000; }
table.shikaku-grid td.shikaku-top { border-top: 2px solid #000; }
table.shikaku-grid td.shikaku-bottom { border-bottom: 2px solid #000; }

.puzzle-explanation-inline {
  font-size: 0.92em; color: #444; margin-top: 0.6em;
}
.puzzle-explanation-footer {
  font-size: 0.85em; color: #555; margin-top: 1em; padding-top: 0.5em;
  border-top: 0.75pt solid #ccc;
}
</style>
"""

# Short German rules blurb per puzzle type - used by the `explanation` option (see
# PuzzleStoryProvider). Kept intentionally brief: this is a reminder, not a rulebook.
_EXPLANATIONS: Dict[str, str] = {
    "sudoku": (
        "Fülle das Raster so, dass in jeder Zeile, jeder Spalte und jedem markierten Block "
        "die Zahlen 1 bis 9 jeweils genau einmal vorkommen."
    ),
    "binoxxo": (
        "Fülle das Raster mit den Symbolen X und O. Nie mehr als zwei gleiche Symbole "
        "direkt nebeneinander oder untereinander, jede Zeile und Spalte enthält gleich "
        "viele X wie O, und keine Zeile bzw. Spalte wiederholt sich."
    ),
    "futoshiki": (
        "Fülle das Raster so, dass in jeder Zeile und jeder Spalte jede Zahl genau einmal "
        "vorkommt. Die Ungleichheitszeichen zwischen benachbarten Feldern müssen erfüllt sein."
    ),
    "kakuro": (
        "Fülle die weißen Felder mit Ziffern von 1 bis 9, sodass jeder zusammenhängende "
        "Zahlenblock in Summe die angegebene Zahl ergibt. Innerhalb eines Blocks darf keine "
        "Ziffer mehrfach vorkommen."
    ),
    "shikaku": (
        "Zerlege das Raster in rechteckige Bereiche, sodass jedes Rechteck genau eine Zahl "
        "enthält und seine Fläche - die Anzahl seiner Felder - dieser Zahl entspricht."
    ),
}

_EXPLANATION_MODES = {"none", "inline", "footer", "appendix"}


# --- Sudoku / Binoxxo: a plain n x n grid, optionally with box divisions -----------------------


def _plain_grid_html(grid, box_size: Optional[int], symbol_for: Callable[[int], str]) -> str:
    rows_html = []
    for r, row in enumerate(grid):
        row_classes = ["box-top"] if box_size and r % box_size == 0 and r > 0 else []
        cells = []
        for c, value in enumerate(row):
            symbol = symbol_for(value) if value is not None else "&nbsp;"
            cell_classes = ["box-left"] if box_size and c % box_size == 0 and c > 0 else []
            cls_attr = f' class="{" ".join(cell_classes)}"' if cell_classes else ""
            cells.append(f"<td{cls_attr}>{symbol}</td>")
        row_attr = f' class="{" ".join(row_classes)}"' if row_classes else ""
        rows_html.append(f"<tr{row_attr}>{''.join(cells)}</tr>")
    return f'<table class="puzzle-grid">{"".join(rows_html)}</table>'


def _render_sudoku(puzzle) -> Tuple[str, str]:
    symbol_for = lambda v: sudoku.SYMBOL_ALPHABET[v]
    return (
        _plain_grid_html(puzzle.givens, puzzle.box_size, symbol_for),
        _plain_grid_html(puzzle.solution, puzzle.box_size, symbol_for),
    )


def _render_binoxxo(puzzle) -> Tuple[str, str]:
    symbol_for = lambda v: binoxxo.DEFAULT_SYMBOLS[v]
    return (
        _plain_grid_html(puzzle.givens, None, symbol_for),
        _plain_grid_html(puzzle.solution, None, symbol_for),
    )


# --- Futoshiki: a grid with inequality signs in the gaps between cells -------------------------


def _futoshiki_html(grid, size: int, constraints) -> str:
    h_ineq: Dict[Tuple[int, int], str] = {}
    v_ineq: Dict[Tuple[int, int], str] = {}
    for constraint in constraints:
        lr, lc = constraint.lesser
        gr, gc = constraint.greater
        if lr == gr:
            left_col = min(lc, gc)
            h_ineq[(lr, left_col)] = "&lt;" if lc < gc else "&gt;"
        else:
            top_row = min(lr, gr)
            v_ineq[(top_row, lc)] = "&and;" if lr < gr else "&or;"

    rows_html = []
    for r in range(size):
        cells = []
        for c in range(size):
            value = grid[r][c]
            symbol = futoshiki.SYMBOL_ALPHABET[value] if value is not None else "&nbsp;"
            cells.append(f'<td class="fut-cell">{symbol}</td>')
            if c < size - 1:
                cells.append(f'<td class="fut-hgap">{h_ineq.get((r, c), "")}</td>')
        rows_html.append(f"<tr>{''.join(cells)}</tr>")
        if r < size - 1:
            gap_cells = []
            for c in range(size):
                gap_cells.append(f'<td class="fut-vgap">{v_ineq.get((r, c), "")}</td>')
                if c < size - 1:
                    gap_cells.append('<td class="fut-spacer"></td>')
            rows_html.append(f"<tr>{''.join(gap_cells)}</tr>")
    return f'<table class="futoshiki-grid">{"".join(rows_html)}</table>'


def _render_futoshiki(puzzle) -> Tuple[str, str]:
    return (
        _futoshiki_html(puzzle.givens, puzzle.size, puzzle.constraints),
        _futoshiki_html(puzzle.solution, puzzle.size, puzzle.constraints),
    )


# --- Kakuro: black clue cells (diagonal split, two sums) + white digit cells -------------------


def _kakuro_html(grid, puzzle) -> str:
    n = puzzle.grid_size
    clue_sums: Dict[Tuple[int, int], Dict[str, int]] = {}
    for run in puzzle.runs:
        clue_sums.setdefault(run.clue_cell, {})[run.orientation] = run.target_sum

    rows_html = []
    for r in range(n):
        cells = []
        for c in range(n):
            if puzzle.black[r][c]:
                sums = clue_sums.get((r, c))
                if sums:
                    h = sums.get("h", "")
                    v = sums.get("v", "")
                    content = (
                        '<div class="kakuro-clue">'
                        f'<span class="kakuro-h">{h}</span>'
                        f'<span class="kakuro-v">{v}</span>'
                        "</div>"
                    )
                else:
                    content = ""
                cells.append(f'<td class="kakuro-black">{content}</td>')
            else:
                value = grid[r][c]
                cells.append(f'<td class="kakuro-white">{value if value is not None else "&nbsp;"}</td>')
        rows_html.append(f"<tr>{''.join(cells)}</tr>")
    return f'<table class="kakuro-grid">{"".join(rows_html)}</table>'


def _render_kakuro(puzzle) -> Tuple[str, str]:
    return (_kakuro_html(puzzle.givens, puzzle), _kakuro_html(puzzle.solution, puzzle))


# --- Shikaku: clue numbers on an empty grid; solution adds rectangle borders --------------------


def _shikaku_owner_map(puzzle):
    owner = [[None] * puzzle.size for _ in range(puzzle.size)]
    for idx, rect in enumerate(puzzle.rectangles):
        for r in range(rect.top, rect.bottom):
            for c in range(rect.left, rect.right):
                owner[r][c] = idx
    return owner


def _shikaku_html(puzzle, owner) -> str:
    size = puzzle.size
    rows_html = []
    for r in range(size):
        cells = []
        for c in range(size):
            classes = []
            if owner is not None:
                if c == size - 1 or owner[r][c] != owner[r][c + 1]:
                    classes.append("shikaku-right")
                if r == size - 1 or owner[r][c] != owner[r + 1][c]:
                    classes.append("shikaku-bottom")
                if c == 0 or owner[r][c] != owner[r][c - 1]:
                    classes.append("shikaku-left")
                if r == 0 or owner[r][c] != owner[r - 1][c]:
                    classes.append("shikaku-top")
            value = puzzle.clues.get((r, c), "")
            cls_attr = f' class="{" ".join(classes)}"' if classes else ""
            cells.append(f"<td{cls_attr}>{value}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")
    return f'<table class="shikaku-grid">{"".join(rows_html)}</table>'


def _render_shikaku(puzzle) -> Tuple[str, str]:
    return (_shikaku_html(puzzle, None), _shikaku_html(puzzle, _shikaku_owner_map(puzzle)))


# --- Provider ------------------------------------------------------------------------------


_GENERATORS = {
    "sudoku": sudoku.generate_puzzle,
    "binoxxo": binoxxo.generate_puzzle,
    "futoshiki": futoshiki.generate_puzzle,
    "kakuro": kakuro.generate_puzzle,
    "shikaku": shikaku.generate_puzzle,
}

_RENDERERS = {
    "sudoku": _render_sudoku,
    "binoxxo": _render_binoxxo,
    "futoshiki": _render_futoshiki,
    "kakuro": _render_kakuro,
    "shikaku": _render_shikaku,
}

# sudoku takes box_size (3 -> 9x9); every other type takes a plain size.
_DEFAULT_SIZE = {
    "binoxxo": binoxxo.DEFAULT_SIZE,
    "futoshiki": futoshiki.DEFAULT_SIZE,
    "kakuro": kakuro.DEFAULT_SIZE,
    "shikaku": shikaku.DEFAULT_SIZE,
}


class PuzzleStoryProvider(StoryProvider):
    """Generates one or more logic puzzles and renders each as an HTML story. Solutions are
    collected separately and placed in the paper's appendix (PlacementPreference.APPENDIX),
    grouped with every other puzzle solution at the very end of the document rather than
    immediately following their own puzzle."""

    def __init__(
        self,
        puzzle_type: str = "sudoku",
        box_size: int = 3,
        size: Optional[int] = None,
        difficulty: str = sudoku.DEFAULT_DIFFICULTY,
        count: int = 1,
        seed: Optional[int] = None,
        explanation: str = "none",
    ) -> None:
        if puzzle_type not in _GENERATORS:
            raise ValueError(
                f'Unknown puzzle_type "{puzzle_type}". Supported: '
                f'{", ".join(sorted(_GENERATORS))}.'
            )
        if explanation not in _EXPLANATION_MODES:
            raise ValueError(
                f'Unknown explanation mode "{explanation}". Supported: '
                f'{", ".join(sorted(_EXPLANATION_MODES))}.'
            )
        self.puzzle_type = puzzle_type
        self.box_size = box_size
        self.size = size
        self.difficulty = difficulty
        self.count = count
        self.seed = seed
        self.explanation = explanation

    def _generate_one(self, rng: random.Random):
        generate = _GENERATORS[self.puzzle_type]
        if self.puzzle_type == "sudoku":
            return generate(box_size=self.box_size, difficulty=self.difficulty, rng=rng)
        size = self.size or _DEFAULT_SIZE[self.puzzle_type]
        return generate(size=size, difficulty=self.difficulty, rng=rng)

    def get_stories(self) -> List[Story]:
        """Puzzles first, then every solution, then (depending on `explanation`) a rules blurb.

        Solutions carry `PlacementPreference.APPENDIX`, so goosepaper collects them - together
        with every other appendix-placed story in the paper, puzzle or not - into one block at
        the very end of the document, each on its own page. That's a deliberate improvement over
        an earlier approach (batching solutions at the end of *this provider's own* story list,
        with `PlacementPreference.FULLPAGE`): FULLPAGE's `break-before: page` does not reliably
        start a new page for a story rendered in place inside a multi-column layout in this
        WeasyPrint version (verified in isolation), so that only really worked under
        `layout: "1col"`. APPENDIX stories render outside any column-count container, so the page
        break is reliable regardless of column layout - see PlacementPreference.APPENDIX.

        `explanation` controls whether/where a short rules blurb for this puzzle_type appears:
          - "none" (default): no blurb.
          - "inline": appended to the end of *every* puzzle instance's own body - expected to
            repeat once per puzzle, the same way a print puzzle book often restates short rules
            next to each puzzle.
          - "footer"/"appendix": one extra Story, in the normal reading-order flow ("footer") or
            grouped into the appendix ("appendix"), *not* one per puzzle instance. Its headline is
            stable per puzzle_type (not per instance/date), so if several sources - even across
            different `count`s or difficulties - all request an explanation for the same
            puzzle_type, Goosepaper's own get_stories(deduplicate=True) collapses them to one
            (same mechanism used for any other cross-provider duplicate; see
            test_goosepaper.py::test_appendix_stories_with_identical_headline_are_deduplicated).
        """
        rng = random.Random(self.seed)
        render = _RENDERERS[self.puzzle_type]
        puzzles: List[Story] = []
        solutions: List[Story] = []
        explanation_text = _EXPLANATIONS[self.puzzle_type]
        for i in range(self.count):
            puzzle = self._generate_one(rng)
            base_label = f"{puzzle.difficulty.title()} {self.puzzle_type.title()}"
            # Disambiguate same type+difficulty instances (count > 1) so their headlines don't
            # collide - Goosepaper's cross-provider deduplicate=True mechanism (see
            # PlacementPreference.APPENDIX's own dedup guarantee) matches on headline+date, and
            # two undated stories with the identical headline "Medium Sudoku" would otherwise
            # silently collapse to one, dropping a whole puzzle (and its solution).
            label = base_label if self.count == 1 else f"{base_label} ({i + 1})"
            givens_html, solution_html = render(puzzle)

            puzzle_html = _PUZZLE_CSS + givens_html
            if self.explanation == "inline":
                puzzle_html += f'<p class="puzzle-explanation-inline">{explanation_text}</p>'

            puzzles.append(
                Story(headline=label, body_html=puzzle_html, short_form=True)
            )
            solutions.append(
                Story(
                    headline=f"{label} - Lösung",
                    body_html=_PUZZLE_CSS + solution_html,
                    include_in_toc=False,
                    short_form=True,
                    placement_preference=PlacementPreference.APPENDIX,
                )
            )

        stories = puzzles + solutions
        if self.explanation in ("footer", "appendix"):
            stories.append(
                Story(
                    headline=f"Wie funktioniert {self.puzzle_type.title()}?",
                    body_html=(
                        _PUZZLE_CSS
                        + f'<p class="puzzle-explanation-footer">{explanation_text}</p>'
                    ),
                    include_in_toc=False,
                    short_form=True,
                    placement_preference=(
                        PlacementPreference.APPENDIX
                        if self.explanation == "appendix"
                        else PlacementPreference.NONE
                    ),
                )
            )
        return stories
