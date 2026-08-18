from .contentfilters import (
    apply_accept_content_filters,
    apply_skip_content_filters,
    should_accept_content,
    should_accept_title,
    should_skip_title,
    visible_text_length,
)


def test_visible_text_length_strips_tags_and_whitespace():
    assert visible_text_length("<p>Hello world</p>") == len("Hello world")


def test_visible_text_length_handles_empty_html():
    assert visible_text_length("") == 0
    assert visible_text_length(None) == 0


def test_css_skip_filter_removes_matching_elements():
    html = '<article><p>Keep me</p><div class="ad">Buy now</div></article>'
    result = apply_skip_content_filters(html, [{"type": "css", "selector": "div.ad"}])

    assert "Buy now" not in result
    assert "Keep me" in result


def test_regex_skip_filter_strips_matching_text():
    html = "<p>Real content. Mehr anzeigen</p>"
    result = apply_skip_content_filters(html, [{"type": "regex", "pattern": "Mehr anzeigen"}])

    assert "Mehr anzeigen" not in result
    assert "Real content." in result


def test_regex_skip_filter_respects_flags():
    html = "<p>MEHR ANZEIGEN</p>"
    result = apply_skip_content_filters(
        html, [{"type": "regex", "pattern": "mehr anzeigen", "flags": "i"}]
    )

    assert "MEHR ANZEIGEN" not in result


def test_regex_skip_filters_run_before_css_skip_filters():
    """Regex operates on the raw string, css on a parsed tree - a filter list combining both
    must apply every regex filter first, then reparse and apply every css filter, regardless of
    the order the two types appear in the list."""
    html = '<div class="drop-me">keep this text, DROP_MARKER too</div>'
    result = apply_skip_content_filters(
        html,
        [
            {"type": "css", "selector": "div.drop-me"},
            {"type": "regex", "pattern": "DROP_MARKER"},
        ],
    )

    assert "keep this text" not in result  # the whole div was dropped by the css filter
    assert "DROP_MARKER" not in result


def test_apply_skip_content_filters_with_no_filters_returns_html_unchanged():
    html = "<p>Untouched</p>"
    assert apply_skip_content_filters(html, []) == html
    assert apply_skip_content_filters(html, None) == html


def test_should_skip_title_matches_any_pattern_case_insensitively():
    patterns = [r"^anzeige:", r"^sponsored"]

    assert should_skip_title("Anzeige: Buy this now", patterns) is True
    assert should_skip_title("Sponsored: another one", patterns) is True
    assert should_skip_title("A regular headline", patterns) is False


def test_should_skip_title_with_no_patterns_never_skips():
    assert should_skip_title("Anything", []) is False


def test_accept_filter_narrows_to_the_matching_container():
    html = '<div class="chrome">Nav junk</div><article class="body"><p>The real story</p></article>'
    result = apply_accept_content_filters(html, [{"type": "css", "selector": "article.body"}])

    assert "The real story" in result
    assert "Nav junk" not in result


def test_accept_filter_tries_selectors_in_order_until_one_matches():
    html = "<div><section class='alt-body'>Found via the second selector</section></div>"
    result = apply_accept_content_filters(
        html,
        [
            {"type": "css", "selector": "article.body"},
            {"type": "css", "selector": "section.alt-body"},
        ],
    )

    assert "Found via the second selector" in result


def test_accept_filter_leaves_html_unchanged_when_nothing_matches():
    html = "<p>Whatever readability extracted</p>"
    result = apply_accept_content_filters(html, [{"type": "css", "selector": "article.body"}])

    assert result == html


def test_accept_filter_ignores_regex_entries():
    """`regex`-type entries are a whole-story gate handled by `should_accept_content`, not a
    transform - `apply_accept_content_filters` only ever acts on `css`-type entries."""
    html = "<p>Whatever readability extracted, mentions AAPL</p>"
    result = apply_accept_content_filters(html, [{"type": "regex", "pattern": "AAPL"}])

    assert result == html


def test_apply_accept_content_filters_with_no_filters_returns_html_unchanged():
    html = "<p>Untouched</p>"
    assert apply_accept_content_filters(html, []) == html
    assert apply_accept_content_filters(html, None) == html


def test_should_accept_title_matches_any_pattern_case_insensitively():
    patterns = ["amazon", "amzn"]

    assert should_accept_title("Amazon stock jumps 5%", patterns) is True
    assert should_accept_title("AMZN hits new high", patterns) is True
    assert should_accept_title("Unrelated market news", patterns) is False


def test_should_accept_title_with_no_patterns_always_accepts():
    assert should_accept_title("Anything at all", []) is True


def test_should_accept_content_with_no_regex_filters_always_accepts():
    """A `css`-type accept filter (or an empty list) has nothing to gate on - only `regex`-type
    entries make this a keep/reject decision."""
    html = "<p>Doesn't mention the ticker at all</p>"
    assert should_accept_content(html, []) is True
    assert should_accept_content(html, [{"type": "css", "selector": "article.body"}]) is True


def test_should_accept_content_matches_regex_against_extracted_text():
    html = "<article><p>AAPL rallies on strong earnings</p></article>"
    assert should_accept_content(html, [{"type": "regex", "pattern": "AAPL"}]) is True
    assert should_accept_content(html, [{"type": "regex", "pattern": "MSFT"}]) is False


def test_should_accept_content_matches_any_regex_filter():
    html = "<p>MSFT climbs after earnings call</p>"
    filters = [
        {"type": "regex", "pattern": "AAPL"},
        {"type": "regex", "pattern": "MSFT"},
    ]

    assert should_accept_content(html, filters) is True


def test_should_accept_content_respects_flags():
    html = "<p>AAPL RALLIES</p>"
    assert should_accept_content(html, [{"type": "regex", "pattern": "aapl"}]) is False
    assert (
        should_accept_content(html, [{"type": "regex", "pattern": "aapl", "flags": "i"}])
        is True
    )


def test_should_accept_content_matches_against_text_not_raw_markup():
    """A pattern shouldn't accidentally match inside a tag or attribute - only the page's
    rendered text counts."""
    html = '<article data-aapl-widget="true"><p>Just talking about oranges</p></article>'

    assert should_accept_content(html, [{"type": "regex", "pattern": "aapl", "flags": "i"}]) is False
