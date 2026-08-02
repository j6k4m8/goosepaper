import re

from .styles import Style


def test_svg_is_constrained_to_the_column_width():
    """An inline <svg> pulled in from article HTML must not render at its own unconstrained
    width/height - see the corner-bracket icon that rendered most of a page tall/wide in a
    narrow column this was fixed for."""
    css = Style("FifthAvenue").get_css(page_profile="paper_pro", layout="2col")

    assert "svg {" in css
    assert "max-width: 100%" in css


def test_unsized_svg_defaults_to_icon_size():
    """readability strips width/height from every <svg> it cleans (verified separately against
    the readability library itself), leaving only a viewBox. A replaced element with no intrinsic
    size defaults to filling its container's available width - max-width: 100% alone doesn't stop
    a small UI icon (a code block's copy/fullscreen button) from rendering as wide as the whole
    column. It needs an actual default size, not just a ceiling."""
    css = Style("FifthAvenue").get_css(page_profile="paper_pro", layout="2col")

    assert "svg:not([width])" in css
    assert "width: 1em" in css


def test_interactive_buttons_are_hidden():
    """Article HTML pulled in via RSS/readability sometimes keeps an interactive <button> from
    the source page - most commonly an image "click to zoom" lightbox trigger (a common
    WordPress/Gutenberg pattern). Its real position/visibility is set by JavaScript that never
    runs here, so unpositioned it falls into normal document flow using the UA stylesheet's
    default <button> styling (grey background, border, rounded corners) - reads as an empty
    flat grey block, since it typically contains only an icon (often invisible against that same
    default grey). No <button> in extracted article prose is ever meaningfully interactive in a
    static, print/PDF context, so every one must be hidden, not just specific known button
    classes from specific sites."""
    css = Style("FifthAvenue").get_css(page_profile="paper_pro", layout="2col")

    assert re.search(r"button\s*{\s*display:\s*none;", css)


def test_appendix_block_gets_exactly_one_page_break_not_per_entry():
    """The appendix (PlacementPreference.APPENDIX) block must start on a fresh page - but only
    once, before the block as a whole, not once per entry inside it (a rule on every entry would
    reintroduce the "wastes a page per solution" behavior this file deliberately removed - see
    the neighboring comment on .appendix > article). break-before: page belongs on .appendix
    itself, never on .appendix > article."""
    css = Style("FifthAvenue").get_css(page_profile="paper_pro", layout="2col")

    assert re.search(r"\.appendix\s*{\s*break-before:\s*page;", css)
    assert not re.search(r"\.appendix\s*>\s*article\s*{[^}]*break-before", css)
