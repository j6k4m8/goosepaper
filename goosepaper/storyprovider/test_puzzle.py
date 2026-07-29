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
