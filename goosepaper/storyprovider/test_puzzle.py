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
