import pytest

from ..goosepaper import Goosepaper
from ..puzzlegen import binoxxo
from .puzzle import PuzzleStoryProvider


def test_puzzle_type_is_required():
    """No default: a config that forgets `puzzle_type` should fail loudly instead of silently
    always generating Sudoku."""
    with pytest.raises(TypeError):
        PuzzleStoryProvider(count=1, seed=1)


def test_size_defaults_to_the_per_difficulty_table_when_unset():
    """Without an explicit `size`, non-sudoku puzzles pick their grid size from the difficulty's
    own table (see e.g. binoxxo/config.py's DIFFICULTIES) instead of one flat default shared by
    every difficulty - "easy" and "hard" must not render the same grid size."""
    easy = PuzzleStoryProvider(puzzle_type="binoxxo", difficulty="easy", count=1, seed=1)
    hard = PuzzleStoryProvider(puzzle_type="binoxxo", difficulty="hard", count=1, seed=1)

    easy_puzzle = next(s for s in easy.get_stories() if not s.headline.endswith("- Lösung"))
    hard_puzzle = next(s for s in hard.get_stories() if not s.headline.endswith("- Lösung"))

    assert easy_puzzle.body_html.count("<tr") == binoxxo.DIFFICULTIES["easy"].size
    assert hard_puzzle.body_html.count("<tr") == binoxxo.DIFFICULTIES["hard"].size
    assert binoxxo.DIFFICULTIES["easy"].size != binoxxo.DIFFICULTIES["hard"].size


def test_explicit_size_overrides_the_difficulty_default():
    provider = PuzzleStoryProvider(
        puzzle_type="binoxxo", difficulty="hard", size=8, count=1, seed=1
    )
    puzzle = next(s for s in provider.get_stories() if not s.headline.endswith("- Lösung"))
    assert puzzle.body_html.count("<tr") == 8


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


def test_two_sources_sharing_type_and_difficulty_lose_one_puzzle_to_dedup():
    """Known limitation, documented on get_stories(): the `count`-loop disambiguation only
    protects against collisions *within* one provider instance. Two separate count=1 providers
    for the same puzzle_type+difficulty still produce the identical internal headline (it's
    derived from type+difficulty only, not from `seed`), so Goosepaper's deduplicate=True
    silently drops one of the two - a real, if narrow, gap this test exists to pin down rather
    than let regress further. If this starts failing because the collision no longer happens,
    that's an improvement - update the docstring in puzzle.py accordingly."""
    first = PuzzleStoryProvider(puzzle_type="sudoku", difficulty="medium", seed=1)
    second = PuzzleStoryProvider(puzzle_type="sudoku", difficulty="medium", seed=2)

    stories = Goosepaper([first, second]).get_stories(deduplicate=True)
    puzzles = [s for s in stories if not s.headline.endswith("- Lösung")]

    assert len(puzzles) == 1  # one of the two genuinely-different puzzles was lost
