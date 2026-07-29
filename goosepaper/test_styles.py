import re

from .styles import Style


def test_appendix_block_gets_exactly_one_page_break_not_per_entry():
    """The appendix (PlacementPreference.APPENDIX) block must start on a fresh page - but only
    once, before the block as a whole, not once per entry inside it (a rule on every entry would
    reintroduce the "wastes a page per solution" behavior this file deliberately removed - see
    the neighboring comment on .appendix > article). break-before: page belongs on .appendix
    itself, never on .appendix > article."""
    css = Style("FifthAvenue").get_css(page_profile="paper_pro", layout="2col")

    assert re.search(r"\.appendix\s*{\s*break-before:\s*page;", css)
    assert not re.search(r"\.appendix\s*>\s*article\s*{[^}]*break-before", css)
