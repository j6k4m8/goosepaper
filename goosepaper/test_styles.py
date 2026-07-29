from .styles import Style


def test_code_blocks_wrap_instead_of_overflowing_the_column():
    """A <pre> block wider than its column must wrap, not overflow into whatever renders next to
    it - see the multi-column overlap this was fixed for."""
    css = Style("FifthAvenue").get_css(page_profile="paper_pro", layout="2col")

    assert "white-space: pre-wrap" in css
    assert "overflow-wrap: break-word" in css
    assert "max-width: 100%" in css
