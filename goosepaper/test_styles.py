from .styles import Style


def test_svg_is_constrained_to_the_column_width():
    """An inline <svg> pulled in from article HTML must not render at its own unconstrained
    width/height - see the corner-bracket icon that rendered most of a page tall/wide in a
    narrow column this was fixed for."""
    css = Style("FifthAvenue").get_css(page_profile="paper_pro", layout="2col")

    assert "svg {" in css
    assert "max-width: 100%" in css
