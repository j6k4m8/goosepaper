import pytest

from ..goosepaper import Goosepaper
from ..util import PlacementPreference
from .puzzle import PuzzleStoryProvider


def test_single_puzzle_headline_has_no_index_suffix():
    provider = PuzzleStoryProvider(puzzle_type="sudoku", count=1, seed=1)
    stories = provider.get_stories()

    puzzles = [s for s in stories if not s.headline.endswith("- Lösung")]
    assert puzzles[0].headline == "Medium Sudoku"


def test_multiple_same_type_puzzles_get_distinct_headlines():
    """Two puzzles of the same type+difficulty (count > 1) must not share a headline: downstream
    consumers (e.g. Goosepaper.get_stories(deduplicate=True), which matches on headline+date)
    would otherwise silently collapse them - and their solutions - down to one."""
    provider = PuzzleStoryProvider(puzzle_type="sudoku", count=2, seed=1)
    stories = provider.get_stories()

    puzzles = [s for s in stories if not s.headline.endswith("- Lösung")]
    solutions = [s for s in stories if s.headline.endswith("- Lösung")]
    assert len(puzzles) == 2
    assert len(solutions) == 2
    assert len({s.headline for s in puzzles}) == 2
    assert len({s.headline for s in solutions}) == 2
    assert puzzles[0].headline == "Medium Sudoku (1)"
    assert puzzles[1].headline == "Medium Sudoku (2)"


def test_solutions_are_placed_in_the_appendix():
    provider = PuzzleStoryProvider(puzzle_type="sudoku", count=2, seed=1)
    stories = provider.get_stories()

    puzzles = [s for s in stories if not s.headline.endswith("- Lösung")]
    solutions = [s for s in stories if s.headline.endswith("- Lösung")]
    assert len(puzzles) == 2
    assert len(solutions) == 2
    assert all(s.placement_preference == PlacementPreference.APPENDIX for s in solutions)
    assert all(s.placement_preference == PlacementPreference.NONE for s in puzzles)


def test_explanation_none_by_default_adds_nothing():
    provider = PuzzleStoryProvider(puzzle_type="sudoku", count=1, seed=1)
    stories = provider.get_stories()

    assert len(stories) == 2  # just the puzzle and its solution
    assert not any("funktioniert" in (s.headline or "") for s in stories)


def test_explanation_inline_is_appended_to_each_puzzle_instance():
    provider = PuzzleStoryProvider(
        puzzle_type="sudoku", count=2, seed=1, explanation="inline"
    )
    stories = provider.get_stories()

    puzzles = [s for s in stories if not s.headline.endswith("- Lösung")]
    assert len(puzzles) == 2
    assert all("puzzle-explanation-inline" in s.body_html for s in puzzles)
    # No separate explanation story is created in inline mode.
    assert len(stories) == 4


def test_explanation_footer_adds_one_story_in_normal_reading_order():
    provider = PuzzleStoryProvider(
        puzzle_type="sudoku", count=2, seed=1, explanation="footer"
    )
    stories = provider.get_stories()

    explanations = [s for s in stories if s.headline == "Wie funktioniert Sudoku?"]
    assert len(explanations) == 1
    assert explanations[0].placement_preference == PlacementPreference.NONE
    assert not explanations[0].include_in_toc
    # One explanation story added on top of the 2 puzzles + 2 solutions.
    assert len(stories) == 5


def test_explanation_footer_uses_a_real_css_footnote():
    """"footer" mode must render as an actual CSS footnote (float: footnote), not a paragraph
    appended to the normal reading flow - see the .puzzle-footnote CSS comment in puzzle.py."""
    provider = PuzzleStoryProvider(puzzle_type="sudoku", count=1, seed=1, explanation="footer")
    stories = provider.get_stories()

    explanation = next(s for s in stories if s.headline == "Wie funktioniert Sudoku?")
    assert "puzzle-footnote" in explanation.body_html
    assert "puzzle-footnote-1" in explanation.body_html  # sudoku is first in _EXPLANATIONS


def test_explanation_footer_marks_every_puzzle_instance_with_a_matching_xref():
    """Every puzzle instance (not just whichever one happens to survive deduplication as the
    carrier of the actual footnote) needs its own visible reference mark, and all of them must
    show the same number as the real footnote - see the .puzzle-footnote CSS comment for why
    that number is fixed per puzzle_type rather than relying on WeasyPrint's own footnote
    counter or target-counter() (neither works for a cross-reference to an existing footnote)."""
    provider = PuzzleStoryProvider(puzzle_type="sudoku", count=2, seed=1, explanation="footer")
    stories = provider.get_stories()

    puzzles = [
        s for s in stories
        if not s.headline.endswith("- Lösung") and not s.headline.startswith("Wie funktioniert")
    ]
    assert len(puzzles) == 2
    for puzzle in puzzles:
        assert '<sup class="puzzle-footnote-xref">1</sup>' in puzzle.body_html


def test_footer_xref_numbers_match_the_footnote_across_sources_and_difficulties():
    """End-to-end through Goosepaper: two sources for the same puzzle_type at different
    difficulties (the real-world shape - e.g. "Sudoku Leicht" and "Sudoku Mittel" as separate
    sections) must both mark their puzzle with the same xref number, and that number must match
    the one real footnote that survives deduplication."""
    easy_sudoku = PuzzleStoryProvider(
        puzzle_type="sudoku", difficulty="easy", seed=1, explanation="footer"
    )
    medium_sudoku = PuzzleStoryProvider(
        puzzle_type="sudoku", difficulty="medium", seed=2, explanation="footer"
    )

    g = Goosepaper([easy_sudoku, medium_sudoku])
    stories = g.get_stories(deduplicate=True)

    explanations = [s for s in stories if s.headline == "Wie funktioniert Sudoku?"]
    assert len(explanations) == 1
    assert "puzzle-footnote-1" in explanations[0].body_html

    puzzles = [
        s for s in stories
        if not s.headline.endswith("- Lösung") and not s.headline.startswith("Wie funktioniert")
    ]
    assert len(puzzles) == 2
    for puzzle in puzzles:
        assert '<sup class="puzzle-footnote-xref">1</sup>' in puzzle.body_html


def test_explanation_appendix_adds_one_story_placed_in_the_appendix():
    provider = PuzzleStoryProvider(
        puzzle_type="sudoku", count=1, seed=1, explanation="appendix"
    )
    stories = provider.get_stories()

    explanations = [s for s in stories if s.headline == "Wie funktioniert Sudoku?"]
    assert len(explanations) == 1
    assert explanations[0].placement_preference == PlacementPreference.APPENDIX


def test_unknown_explanation_mode_is_rejected():
    with pytest.raises(ValueError):
        PuzzleStoryProvider(puzzle_type="sudoku", explanation="somewhere-else")


def test_repeated_appendix_explanations_across_sources_are_deduplicated():
    """Two separate PuzzleStoryProvider instances (as two "puzzle" sources in a real config
    would produce) both requesting an appendix explanation for the same puzzle_type should
    only contribute one explanation story to the rendered paper - proven end-to-end through
    Goosepaper itself, not just at the provider level."""
    easy_sudoku = PuzzleStoryProvider(
        puzzle_type="sudoku", difficulty="easy", seed=1, explanation="appendix"
    )
    hard_sudoku = PuzzleStoryProvider(
        puzzle_type="sudoku", difficulty="hard", seed=2, explanation="appendix"
    )

    g = Goosepaper([easy_sudoku, hard_sudoku])
    stories = g.get_stories(deduplicate=True)

    explanations = [s for s in stories if s.headline == "Wie funktioniert Sudoku?"]
    assert len(explanations) == 1


def test_no_name_shows_no_visible_label():
    """Without `name`, a puzzle relies entirely on its enclosing section's own heading - no
    auto-generated "Medium Sudoku" text should render (it still exists as the Story's internal
    `headline`, for dedup/anchor-uniqueness - see get_stories()'s docstring - just not shown)."""
    provider = PuzzleStoryProvider(puzzle_type="sudoku", count=1, seed=1)
    stories = provider.get_stories()

    for story in stories:
        assert '<h2 class="puzzle-custom-label">' not in story.body_html
    # The internal identity is untouched by the absence of `name`.
    puzzles = [s for s in stories if not s.headline.endswith("- Lösung")]
    assert puzzles[0].headline == "Medium Sudoku"


def test_name_becomes_the_visible_label_instead_of_the_auto_generated_text():
    provider = PuzzleStoryProvider(puzzle_type="sudoku", count=1, seed=1, name="Sudoku Mittel")
    stories = provider.get_stories()

    puzzle = next(s for s in stories if not s.headline.endswith("- Lösung"))
    solution = next(s for s in stories if s.headline.endswith("- Lösung"))
    assert '<h2 class="puzzle-custom-label">Sudoku Mittel</h2>' in puzzle.body_html
    assert '<h2 class="puzzle-custom-label">Sudoku Mittel - Lösung</h2>' in solution.body_html
    # The internal identity (headline) is still the disambiguated auto-generated label, not
    # `name` - so cross-source dedup/anchor uniqueness keeps working exactly as before,
    # regardless of what a user names two otherwise-different puzzle instances.
    assert puzzle.headline == "Medium Sudoku"


def test_custom_name_is_html_escaped():
    provider = PuzzleStoryProvider(
        puzzle_type="sudoku", count=1, seed=1, name="<script>alert(1)</script>"
    )
    stories = provider.get_stories()

    puzzle = next(s for s in stories if not s.headline.endswith("- Lösung"))
    assert "<script>" not in puzzle.body_html
    assert "&lt;script&gt;" in puzzle.body_html
