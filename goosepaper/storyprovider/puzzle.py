"""Logic puzzles (Sudoku, Binoxxo, Futoshiki, Kakuro, Shikaku) rendered as plain HTML - tables,
inline CSS, nothing else.

Generation lives in :mod:`goosepaper.puzzlegen` - vendored, dependency-free grid/solver code with
no rendering of its own, one subpackage per puzzle type. This module owns all rendering. No image
rasterization, no reportlab, nothing beyond what WeasyPrint (goosepaper's existing HTML-to-PDF
renderer) already handles.
"""

from __future__ import annotations

import importlib.resources as resources
import random
from html import escape
from typing import Callable, Container, Dict, List, Literal, Optional, Tuple

from ..puzzlegen import binoxxo, futoshiki, kakuro, shikaku, sudoku
from ..story import Story
from ..util import PlacementPreference
from .storyprovider import StoryProvider

# Static CSS for every puzzle type lives in puzzle.css, right next to this module - kept as a
# real .css file (not an f-string) since none of it needs Python-side interpolation, so it gets
# proper syntax highlighting/linting and stays free of Python string-escaping concerns even
# though it's dense with explanatory comments about WeasyPrint quirks.
_PUZZLE_CSS = (
    "<style>"
    + resources.files(__package__).joinpath("puzzle.css").read_text(encoding="utf-8")
    + "</style>"
)

# Short rules blurb per puzzle type - used by the `explanation` option (see
# PuzzleStoryProvider). Kept intentionally brief: this is a reminder, not a rulebook.
_EXPLANATIONS: Dict[str, str] = {
    "sudoku": (
        "Fill the grid so that the numbers 1 to 9 each appear exactly once in every row, "
        "column, and marked block."
    ),
    "binoxxo": (
        "Fill the grid with the symbols X and O. No more than two identical symbols in a "
        "row or column, each row and column contains an equal number of Xs and Os, and no "
        "row or column repeats."
    ),
    "futoshiki": (
        "Fill the grid so that every number appears exactly once in each row and each "
        "column. The inequality signs between neighboring cells must be satisfied."
    ),
    "kakuro": (
        "Fill the white cells with digits from 1 to 9 so that each contiguous block of "
        "digits sums to the given number. No digit may repeat within a block."
    ),
    "shikaku": (
        "Divide the grid into rectangular regions so that each rectangle contains exactly "
        "one number, and its area - the number of its cells - matches that number."
    ),
}

# Kept in sync with _EXPLANATION_MODES by hand - Literal can't be built from a set's members at
# type-check time, so this is the closest editors get to intellisense/hinting on `explanation`.
ExplanationMode = Literal["none", "inline", "footer", "appendix"]

_EXPLANATION_MODES = {"none", "inline", "footer", "appendix"}

# Fixed per-type footnote number for "footer" mode - see the .puzzle-footnote CSS comment above
# for why this can't just be WeasyPrint's own auto-incrementing `footnote` counter.
_EXPLANATION_NUMBER: Dict[str, int] = {name: i + 1 for i, name in enumerate(_EXPLANATIONS)}


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
    def symbol_for(v):
        return sudoku.SYMBOL_ALPHABET[v]

    return (
        _plain_grid_html(puzzle.givens, puzzle.box_size, symbol_for),
        _plain_grid_html(puzzle.solution, puzzle.box_size, symbol_for),
    )


def _render_binoxxo(puzzle) -> Tuple[str, str]:
    def symbol_for(v):
        return binoxxo.DEFAULT_SYMBOLS[v]

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
                        '<table class="kakuro-clue"><tr>'
                        f'<td></td><td class="kakuro-h">{h}</td>'
                        "</tr><tr>"
                        f'<td class="kakuro-v">{v}</td><td></td>'
                        "</tr></table>"
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


# Kept in sync with _GENERATORS' keys by hand - Literal can't be built from a dict's keys at
# type-check time, so this is the closest editors get to intellisense/hinting on `puzzle_type`.
PuzzleType = Literal["sudoku", "binoxxo", "futoshiki", "kakuro", "shikaku"]

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

# sudoku takes box_size (3 -> 9x9, independent of difficulty - see PuzzleStoryProvider's
# `box_size` docstring); every other type's grid size is derived from `difficulty` instead
# (see _generate_one) - each type's own DIFFICULTIES table pairs a larger grid with its
# harder presets (most visibly shikaku, where "hard" is specifically measured/tuned for a
# 20x20 grid), so there's no separate `size` knob to set independently of `difficulty` -
# doing so could ask for combinations the generator was never measured against.
_DIFFICULTIES = {
    "binoxxo": binoxxo.DIFFICULTIES,
    "futoshiki": futoshiki.DIFFICULTIES,
    "kakuro": kakuro.DIFFICULTIES,
    "shikaku": shikaku.DIFFICULTIES,
}


def _validate_choice(value: str, valid: Container[str], label: str) -> None:
    if value not in valid:
        raise ValueError(f'Unknown {label} "{value}". Supported: {", ".join(sorted(valid))}.')


class PuzzleStoryProvider(StoryProvider):
    """Generates one or more logic puzzles and renders each as an HTML story. Solutions are
    collected separately and placed in the paper's appendix (PlacementPreference.APPENDIX),
    grouped with every other puzzle solution at the very end of the document rather than
    immediately following their own puzzle.

    Constructor parameters:
      - `puzzle_type` (required): one of "sudoku", "binoxxo", "futoshiki", "kakuro", "shikaku".
        No default - a config that forgets it should fail loudly instead of silently always
        generating Sudoku.
      - `box_size` (optional, default 3): **sudoku only**, ignored for every other type.
        Supported values are `2` (4x4, a quick/easy variant) and `3` (the classic 9x9, 3x3
        boxes). Unlike every other type's grid size, this does not vary by `difficulty` - all
        three difficulties use the same box size, so there is no per-difficulty table for it.
      - `difficulty` (optional, default "medium"): one of "easy", "medium", "hard". Controls
        how many cells/constraints are given (see each type's own `DIFFICULTIES` table) and,
        for every type but sudoku, the grid size itself - see e.g. `binoxxo/config.py`'s
        `DIFFICULTIES` table for the exact per-difficulty sizes and why grid size and
        difficulty aren't independent knobs to begin with.
      - `count` (optional, default 1): how many puzzle instances of this type+difficulty to
        generate.
      - `seed` (optional, default None): RNG seed, for reproducible generation.
      - `explanation` (optional, default "none"): whether/where a short rules blurb for this
        puzzle_type appears - see get_stories()'s docstring for the "none"/"inline"/"footer"/
        "appendix" modes.
      - `name` (optional, default None): visible per-instance heading - see get_stories()'s
        docstring for the "no name -> no heading, just the section's own" behavior.
    """

    def __init__(
        self,
        puzzle_type: PuzzleType,
        box_size: int = 3,
        difficulty: str = sudoku.DEFAULT_DIFFICULTY,
        count: int = 1,
        seed: Optional[int] = None,
        explanation: ExplanationMode = "none",
        name: Optional[str] = None,
    ) -> None:
        _validate_choice(puzzle_type, _GENERATORS, "puzzle_type")
        _validate_choice(explanation, _EXPLANATION_MODES, "explanation mode")
        self.puzzle_type = puzzle_type
        self.box_size = box_size
        self.difficulty = difficulty
        self.count = count
        self.seed = seed
        self.explanation = explanation
        self.name = name

    def _generate_one(self, rng: random.Random):
        generate = _GENERATORS[self.puzzle_type]
        if self.puzzle_type == "sudoku":
            return generate(box_size=self.box_size, difficulty=self.difficulty, rng=rng)
        size = _DIFFICULTIES[self.puzzle_type][self.difficulty].size
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
          - "footer": a real CSS footnote (`float: footnote`, see the .puzzle-footnote CSS
            comment) - lands at the bottom of whichever page it's on, not glued into the reading
            flow. One extra Story carries the actual footnote content; every puzzle instance of
            this type (including repeats across difficulties/sources) gets its own small
            `.puzzle-footnote-xref` reference mark instead of its own copy of the explanation.
          - "appendix": one extra Story, grouped into the paper's appendix alongside solutions -
            not one per puzzle instance, no reference mark at each puzzle (the appendix is already
            a distinct "endnotes" section, unlike "footer"'s inline-adjacent placement).
          Both "footer" and "appendix" use a stable per-puzzle_type headline (not per instance/
          date), so if several sources - even across different `count`s or difficulties - all
          request an explanation for the same puzzle_type, Goosepaper's own
          get_stories(deduplicate=True) collapses the extra Story down to one (same mechanism used
          for any other cross-provider duplicate; see
          test_goosepaper.py::test_appendix_stories_with_identical_headline_are_deduplicated).

        Visible heading: this provider does not display its own generated "Medium Sudoku"-style
        text (that internal label still becomes the Story's `headline` - Goosepaper's own
        cross-provider deduplicate=True and per-story anchor-uniqueness machinery both need a
        stable, distinct identity per story regardless of what's configured, and the label
        supplies that - it's just never rendered, see the .puzzle-body CSS rule above). What
        *does* show, per puzzle instance, is:
          - `name`, if given, as that instance's own heading; the same text (plus " - Solution")
            on its solution.
          - nothing, if `name` isn't given - only the enclosing section's own heading identifies
            what the reader is looking at. Fine when a section already covers exactly one
            type+difficulty (e.g. a "Sudoku Mittel" section with only sudoku/medium sources in
            it); with several different puzzle types sharing one section, an unset `name` means
            no per-instance way to tell them apart.

        Known limitation - headline collisions *across* separate provider instances: the `(i+1)`
        suffix below only disambiguates puzzles generated by *this* `count` loop, and the label
        it's added to (see `base_label`) is derived purely from `puzzle_type` + `difficulty` -
        not from `seed`, which affects only the generated content, never the headline. Two
        separate `PuzzleStoryProvider` instances (e.g. two "puzzle" sources in a config) that
        share the same `puzzle_type` + `difficulty` and both leave `count` at its default of 1
        will produce two Stories with the identical internal headline (e.g. two "Medium Sudoku"
        stories, each with genuinely different content) - Goosepaper's `deduplicate=True` matches
        on headline+date, so one of the two silently disappears along with its solution, the same
        failure mode this loop exists to prevent, just one level up. If you want several instances
        of the same `puzzle_type` + `difficulty`, use a single source with `count` set to that
        many (its own `(i+1)` suffixes keep them apart) rather than several separate `count: 1`
        sources - a different `seed` alone does not help here.
        """
        rng = random.Random(self.seed)
        render = _RENDERERS[self.puzzle_type]
        puzzles: List[Story] = []
        solutions: List[Story] = []
        explanation_text = _EXPLANATIONS[self.puzzle_type]
        footnote_number = _EXPLANATION_NUMBER[self.puzzle_type]
        for i in range(self.count):
            puzzle = self._generate_one(rng)
            base_label = f"{puzzle.difficulty.title()} {self.puzzle_type.title()}"
            # Disambiguate same type+difficulty instances (count > 1) so their headlines don't
            # collide - Goosepaper's cross-provider deduplicate=True mechanism (see
            # PlacementPreference.APPENDIX's own dedup guarantee) matches on headline+date, and
            # two undated stories with the identical headline "Medium Sudoku" would otherwise
            # silently collapse to one, dropping a whole puzzle (and its solution). This is the
            # Story's internal `headline` only now - see get_stories()'s docstring for why it's
            # never the visible text.
            label = base_label if self.count == 1 else f"{base_label} ({i + 1})"
            givens_html, solution_html = render(puzzle)

            visible_label = (
                f'<h2 class="puzzle-custom-label">{escape(self.name)}</h2>' if self.name else ""
            )
            visible_solution_label = (
                f'<h2 class="puzzle-custom-label">{escape(self.name)} - Solution</h2>'
                if self.name
                else ""
            )

            puzzle_content = visible_label + givens_html
            if self.explanation == "inline":
                puzzle_content += f'<p class="puzzle-explanation-inline">{explanation_text}</p>'
            elif self.explanation == "footer":
                # Every instance gets the reference mark, not just whichever one happens to carry
                # the actual footnote after dedup (see get_stories()'s docstring) - the reader
                # sees the same small number next to every "Sudoku" puzzle, regardless of
                # difficulty, all pointing at the one explanation that survives deduplication.
                puzzle_content += (
                    f'<sup class="puzzle-footnote-xref">{footnote_number}</sup>'
                )

            puzzles.append(
                Story(
                    headline=label,
                    body_html=(
                        _PUZZLE_CSS + f'<div class="puzzle-body">{puzzle_content}</div>'
                    ),
                    short_form=True,
                )
            )
            solutions.append(
                Story(
                    headline=f"{label} - Solution",
                    body_html=(
                        _PUZZLE_CSS
                        + f'<div class="puzzle-body">{visible_solution_label}{solution_html}</div>'
                    ),
                    include_in_toc=False,
                    short_form=True,
                    placement_preference=PlacementPreference.APPENDIX,
                )
            )

        stories = puzzles + solutions
        if self.explanation == "footer":
            stories.append(
                Story(
                    headline=f"How does {self.puzzle_type.title()} work?",
                    body_html=(
                        _PUZZLE_CSS
                        + f'<span class="puzzle-footnote puzzle-footnote-{footnote_number}">'
                        f"{explanation_text}</span>"
                    ),
                    include_in_toc=False,
                    short_form=True,
                    placement_preference=PlacementPreference.NONE,
                )
            )
        elif self.explanation == "appendix":
            stories.append(
                Story(
                    headline=f"How does {self.puzzle_type.title()} work?",
                    body_html=(
                        _PUZZLE_CSS
                        + f'<p class="puzzle-explanation-footer">{explanation_text}</p>'
                    ),
                    include_in_toc=False,
                    short_form=True,
                    placement_preference=PlacementPreference.APPENDIX,
                )
            )
        return stories
