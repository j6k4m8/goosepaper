import pytest

from ..goosepaper import Goosepaper
from ..util import PlacementPreference
from .puzzle import PuzzleStoryProvider


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
