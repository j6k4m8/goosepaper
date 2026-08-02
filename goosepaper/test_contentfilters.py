from .contentfilters import (
    apply_content_accept_filters,
    apply_content_filters,
    should_accept_title,
    should_skip_title,
)


def test_css_filter_removes_matching_elements():
    html = '<article><p>Keep me</p><div class="ad">Buy now</div></article>'
    result = apply_content_filters(html, [{"type": "css", "selector": "div.ad"}])

    assert "Buy now" not in result
    assert "Keep me" in result


def test_regex_filter_strips_matching_text():
    html = "<p>Real content. Mehr anzeigen</p>"
    result = apply_content_filters(html, [{"type": "regex", "pattern": "Mehr anzeigen"}])

    assert "Mehr anzeigen" not in result
    assert "Real content." in result


def test_regex_filter_respects_flags():
    html = "<p>MEHR ANZEIGEN</p>"
    result = apply_content_filters(
        html, [{"type": "regex", "pattern": "mehr anzeigen", "flags": "i"}]
    )

    assert "MEHR ANZEIGEN" not in result


def test_regex_filters_run_before_css_filters():
    """Regex operates on the raw string, css on a parsed tree - a filter list combining both
    must apply every regex filter first, then reparse and apply every css filter, regardless of
    the order the two types appear in the list."""
    html = '<div class="drop-me">keep this text, DROP_MARKER too</div>'
    result = apply_content_filters(
        html,
        [
            {"type": "css", "selector": "div.drop-me"},
            {"type": "regex", "pattern": "DROP_MARKER"},
        ],
    )

    assert "keep this text" not in result  # the whole div was dropped by the css filter
    assert "DROP_MARKER" not in result


def test_apply_content_filters_with_no_filters_returns_html_unchanged():
    html = "<p>Untouched</p>"
    assert apply_content_filters(html, []) == html
    assert apply_content_filters(html, None) == html


def test_should_skip_title_matches_any_pattern_case_insensitively():
    patterns = [r"^anzeige:", r"^sponsored"]

    assert should_skip_title("Anzeige: Buy this now", patterns) is True
    assert should_skip_title("Sponsored: another one", patterns) is True
    assert should_skip_title("A regular headline", patterns) is False


def test_should_skip_title_with_no_patterns_never_skips():
    assert should_skip_title("Anything", []) is False


def test_accept_filter_narrows_to_the_matching_container():
    html = '<div class="chrome">Nav junk</div><article class="body"><p>The real story</p></article>'
    result = apply_content_accept_filters(html, [{"selector": "article.body"}])

    assert "The real story" in result
    assert "Nav junk" not in result


def test_accept_filter_tries_selectors_in_order_until_one_matches():
    html = "<div><section class='alt-body'>Found via the second selector</section></div>"
    result = apply_content_accept_filters(
        html, [{"selector": "article.body"}, {"selector": "section.alt-body"}]
    )

    assert "Found via the second selector" in result


def test_accept_filter_leaves_html_unchanged_when_nothing_matches():
    html = "<p>Whatever readability extracted</p>"
    result = apply_content_accept_filters(html, [{"selector": "article.body"}])

    assert result == html


def test_apply_content_accept_filters_with_no_filters_returns_html_unchanged():
    html = "<p>Untouched</p>"
    assert apply_content_accept_filters(html, []) == html
    assert apply_content_accept_filters(html, None) == html


def test_should_accept_title_matches_any_pattern_case_insensitively():
    patterns = ["amazon", "amzn"]

    assert should_accept_title("Amazon stock jumps 5%", patterns) is True
    assert should_accept_title("AMZN hits new high", patterns) is True
    assert should_accept_title("Unrelated market news", patterns) is False


def test_should_accept_title_with_no_patterns_always_accepts():
    assert should_accept_title("Anything at all", []) is True
