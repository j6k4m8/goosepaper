"""Logic puzzles (Sudoku, Binoxxo, Futoshiki, Kakuro, Shikaku) rendered as plain HTML - tables,
inline CSS, nothing else.

Generation lives in :mod:`goosepaper.puzzlegen` - vendored, dependency-free grid/solver code with
no rendering of its own, one subpackage per puzzle type. This module owns all rendering. No image
rasterization, no reportlab, nothing beyond what WeasyPrint (goosepaper's existing HTML-to-PDF
renderer) already handles.
"""

from __future__ import annotations

import random
from html import escape
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
/* The clue cell's diagonal (linear-gradient(to top right, ...) above) splits it into an
upper-right triangle (the row/"h" sum, i.e. the sum of the white run to the right) and a
lower-left triangle (the column/"v" sum, the run going down - see kakuro/rules.py's Run
docstring). WeasyPrint inverts the vertical axis for an absolutely-positioned span nested this
way inside a table cell (position:relative div -> position:relative td): "top: 0" renders at the
visual bottom and "bottom: 0" renders at the visual top, confirmed by rendering an isolated
labelled cell. `bottom`/`top` below are therefore intentionally the opposite of where each label
visually needs to land - swapping them is what actually puts "h" at the top (of the upper-right
triangle) and "v" at the bottom (of the lower-left triangle). */
table.kakuro-grid .kakuro-h { position: absolute; bottom: 0; right: 2px; font-size: 0.5em; color: #fff; }
table.kakuro-grid .kakuro-v { position: absolute; top: 0; left: 2px; font-size: 0.5em; color: #fff; }

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

/* "footer" explanations are real CSS footnotes (float: footnote), not a paragraph glued onto the
end of a puzzle's own body - so they land at the bottom of whichever page they end up on instead
of interrupting the reading flow. Deduplication (see get_stories()'s docstring) means only one
puzzle_type's worth of footnote content actually exists per document; every puzzle instance that
type appears in - including repeats across difficulties - carries its own .puzzle-footnote-xref
marker instead, showing the same number. WeasyPrint's own auto-numbering (the `footnote` CSS
counter) can't be reused for that: it counts every float: footnote in the whole document in
order, so a later instance's marker would show a different, unrelated number - there's also no
working way in this WeasyPrint version to point a plain cross-reference at "whatever number this
other footnote got" (target-counter() was tried; it did not resolve). So the number is entirely
our own - fixed per puzzle_type (see _EXPLANATION_NUMBER) - and both the floated footnote's own
marker and every xref marker render that literal digit, with WeasyPrint's own footnote-call/
footnote-marker auto-generated content suppressed. */
.puzzle-footnote { float: footnote; }
.puzzle-footnote::footnote-call { content: ""; }
.puzzle-footnote-xref { vertical-align: super; font-size: 0.7em; line-height: 0; }
/* The explanation Story's own headline ("Wie funktioniert Sudoku?") is a sibling of .story-body,
not something float: footnote takes with it - only the .puzzle-footnote span floats away, leaving
the heading behind as an orphaned line with nothing under it. Hide it: the Story still needs a
real, stable headline for Goosepaper's own deduplicate=True matching (see get_stories()'s
docstring), it just shouldn't render as a visible section of its own. Same story for the
surrounding <article>'s own divider (margin/padding/border-bottom, from the base .main-stories >
article rule) - with headline and body both gone/floated, an empty divider line would be all
that's left behind in the normal flow. */
article:has(.puzzle-footnote) > .story-headline { display: none; }
article:has(.puzzle-footnote) { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
.puzzle-footnote-1::footnote-marker { content: "1. "; }
.puzzle-footnote-2::footnote-marker { content: "2. "; }
.puzzle-footnote-3::footnote-marker { content: "3. "; }
.puzzle-footnote-4::footnote-marker { content: "4. "; }
.puzzle-footnote-5::footnote-marker { content: "5. "; }

/* PuzzleStoryProvider no longer shows its own auto-generated "Medium Sudoku"-style label (see
get_stories()'s docstring) - that text still exists as the Story's actual `headline`, since
Goosepaper's own cross-provider dedup/anchor-uniqueness machinery needs a stable, distinct
identity per story regardless of what's configured, but it's never rendered: config-driven
`name`, if given, or nothing (relying on the enclosing section's own heading) is the point. */
article:has(.puzzle-body) > .story-headline { display: none; }
.puzzle-custom-label { margin: 0 0 0.4em; font-size: 1.05em; font-weight: bold; }
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
        puzzle_type: str,
        box_size: int = 3,
        difficulty: str = sudoku.DEFAULT_DIFFICULTY,
        count: int = 1,
        seed: Optional[int] = None,
        explanation: str = "none",
        name: Optional[str] = None,
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
          - `name`, if given, as that instance's own heading; the same text (plus " - Lösung")
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
                f'<h2 class="puzzle-custom-label">{escape(self.name)} - Lösung</h2>'
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
                    headline=f"{label} - Lösung",
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
                    headline=f"Wie funktioniert {self.puzzle_type.title()}?",
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
                    headline=f"Wie funktioniert {self.puzzle_type.title()}?",
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
