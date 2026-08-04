import datetime
from types import SimpleNamespace

from . import rss


def _feed_entry(
    *,
    title="Feed title",
    summary="<p>Feed summary</p>",
    link="https://example.com/story",
    content=None,
):
    payload = {
        "title": title,
        "updated_parsed": datetime.datetime(
            2026,
            4,
            23,
            9,
            0,
            0,
        ).timetuple(),
    }
    if summary is not None:
        payload["summary"] = summary
    if link is not None:
        payload["link"] = link
    if content is not None:
        payload["content"] = content
    return rss.feedparser.FeedParserDict(payload)


class _FakeResponse:
    def __init__(
        self,
        *,
        ok=True,
        text="<html></html>",
        content=b"<html></html>",
        encoding="utf-8",
        url="https://example.com/story",
    ):
        self.ok = ok
        self.text = text
        self.content = content
        self.encoding = encoding
        self.url = url


def test_rss_provider_prefers_embedded_feed_content(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    content=[
                        rss.feedparser.FeedParserDict(
                            {"value": "<p>Embedded story body</p>"}
                        )
                    ]
                )
            ]
        ),
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not run when feed content exists")

    monkeypatch.setattr(rss.requests, "get", fail_get)

    provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
    stories = provider.get_stories()

    assert stories[0].headline == "Feed title"
    assert stories[0].body_html == "<p>Embedded story body</p>"
    assert stories[0].byline == "example.com"


def test_rss_provider_summary_mode_uses_feed_summary(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    summary="<p>Feed summary only</p>",
                    content=[
                        rss.feedparser.FeedParserDict(
                            {"value": "<p>Embedded story body</p>"}
                        )
                    ],
                )
            ]
        ),
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not run in summary mode")

    monkeypatch.setattr(rss.requests, "get", fail_get)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        body_source="summary",
    )
    stories = provider.get_stories()

    assert stories[0].body_html == "<p>Feed summary only</p>"


def test_rss_provider_content_mode_uses_feed_content_without_article_fetch(
    monkeypatch,
):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    summary="<p>Feed summary only</p>",
                    content=[
                        rss.feedparser.FeedParserDict(
                            {"value": "<p>Embedded story body</p>"}
                        )
                    ],
                )
            ]
        ),
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not run in content mode")

    monkeypatch.setattr(rss.requests, "get", fail_get)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        body_source="content",
    )
    stories = provider.get_stories()

    assert stories[0].body_html == "<p>Embedded story body</p>"


def test_rss_provider_content_mode_falls_back_to_summary(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[_feed_entry(summary="<p>Feed summary only</p>", content=None)]
        ),
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not run in content mode")

    monkeypatch.setattr(rss.requests, "get", fail_get)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        body_source="content",
    )
    stories = provider.get_stories()

    assert stories[0].body_html == "<p>Feed summary only</p>"


def test_rss_provider_passes_text_to_readability(monkeypatch):
    seen = {}

    class FakeDocument:
        def __init__(self, html):
            seen["html"] = html

        def title(self):
            return "Readable title"

        def summary(self):
            return "<p>Readable summary</p>"

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[_feed_entry(summary=None)]),
    )
    monkeypatch.setattr(
        rss.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(
            ok=True,
            text="<html><body>decoded</body></html>",
            content=b"<html><body>bytes</body></html>",
        ),
    )
    monkeypatch.setattr(rss, "Document", FakeDocument)

    provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
    stories = provider.get_stories()

    assert isinstance(seen["html"], str)
    assert stories[0].headline == "Readable title"
    assert stories[0].body_html == "<p>Readable summary</p>"


def test_rss_provider_prefer_feed_title_overrides_readability_title(monkeypatch):
    class FakeDocument:
        def __init__(self, html):
            pass

        def title(self):
            return "Golem.de"  # e.g. readability returning just the site name

        def summary(self):
            return "<p>Readable summary</p>"

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[_feed_entry(title="The actual headline", summary=None)]),
    )
    monkeypatch.setattr(
        rss.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(ok=True, text="<html></html>"),
    )
    monkeypatch.setattr(rss, "Document", FakeDocument)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        prefer_feed_title=True,
    )
    stories = provider.get_stories()

    assert stories[0].headline == "The actual headline"


def test_rss_provider_prefer_feed_title_defaults_to_false(monkeypatch):
    class FakeDocument:
        def __init__(self, html):
            pass

        def title(self):
            return "Readable title"

        def summary(self):
            return "<p>Readable summary</p>"

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[_feed_entry(summary=None)]),
    )
    monkeypatch.setattr(
        rss.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(ok=True, text="<html></html>"),
    )
    monkeypatch.setattr(rss, "Document", FakeDocument)

    provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
    stories = provider.get_stories()

    assert stories[0].headline == "Readable title"


def test_rss_provider_article_mode_fetches_article_even_when_feed_has_content(
    monkeypatch,
):
    seen = {"requests": 0}

    class FakeDocument:
        def __init__(self, html):
            self.html = html

        def title(self):
            return "Readable title"

        def summary(self):
            return "<p>Readable summary</p>"

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    content=[
                        rss.feedparser.FeedParserDict(
                            {"value": "<p>Embedded story body</p>"}
                        )
                    ]
                )
            ]
        ),
    )

    def fake_get(*args, **kwargs):
        seen["requests"] += 1
        return _FakeResponse(ok=True, text="<html><body>decoded</body></html>")

    monkeypatch.setattr(rss.requests, "get", fake_get)
    monkeypatch.setattr(rss, "Document", FakeDocument)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        body_source="article",
    )
    stories = provider.get_stories()

    assert seen["requests"] == 1
    assert stories[0].headline == "Readable title"
    assert stories[0].body_html == "<p>Readable summary</p>"


class TestMakeUrlsAbsolute:
    def test_resolves_a_root_relative_image_src(self):
        html = '<img src="/assets/img/webp/29/03/22-2024-car-and-driver-logo.webp">'

        result = rss._make_urls_absolute(
            html, "https://www.caranddriver.com/features/a12345/some-article/"
        )

        assert result == (
            '<img src="https://www.caranddriver.com/assets/img/webp/29/03/'
            '22-2024-car-and-driver-logo.webp"/>'
        )

    def test_resolves_a_page_relative_link_href(self):
        html = '<a href="../other-story/">read more</a>'

        result = rss._make_urls_absolute(
            html, "https://example.com/section/this-story/"
        )

        assert result == (
            '<a href="https://example.com/section/other-story/">read more</a>'
        )

    def test_leaves_already_absolute_urls_alone(self):
        # Value is untouched; the self-closing "/>" is just lxml's normal serialization, applied
        # unconditionally now (see test_strips_a_synthetic_html_body_wrapper_... above for why).
        html = '<img src="https://cdn.example.com/foo.jpg">'

        result = rss._make_urls_absolute(html, "https://example.com/story/")

        assert result == '<img src="https://cdn.example.com/foo.jpg"/>'

    def test_resolves_a_protocol_relative_image_src(self):
        # Regression test: matches a real failure seen in production - "Failed to load image at
        # 'file://images.cgames.de/images/gamestar/290/foo.jpg': ... No such file or directory".
        # A protocol-relative URL ("//host/path") parses with a netloc but no scheme, so an
        # earlier version of this function's `urlparse(value).netloc` check mistook it for
        # already-absolute and left it untouched - it then got resolved later against the
        # newspaper's file:// base_url instead of the article's own https:// URL, producing a
        # broken "file://host/path" URL.
        html = '<img src="//images.cgames.de/images/gamestar/290/foo.jpg">'

        result = rss._make_urls_absolute(html, "https://www.gamestar.de/artikel/foo,123.html")

        assert result == '<img src="https://images.cgames.de/images/gamestar/290/foo.jpg"/>'

    def test_leaves_data_uris_alone(self):
        html = '<img src="data:image/png;base64,aGVsbG8=">'

        result = rss._make_urls_absolute(html, "https://example.com/story/")

        assert result == '<img src="data:image/png;base64,aGVsbG8="/>'

    def test_does_not_leak_a_synthetic_body_wrapper(self):
        html = '<p>hello</p><img src="/foo.jpg">'

        result = rss._make_urls_absolute(html, "https://example.com/")

        assert result == '<p>hello</p><img src="https://example.com/foo.jpg"/>'

    def test_noop_when_nothing_needed_absolutizing(self):
        # Content is unchanged (though re-serialized, not the exact same string object - see
        # test_strips_a_synthetic_html_body_wrapper_even_with_nothing_to_absolutize below for why
        # re-serializing unconditionally, not just when something changed, is required).
        html = "<p>plain text, no urls here</p>"

        result = rss._make_urls_absolute(html, "https://example.com/story/")

        assert result == html

    def test_strips_a_synthetic_html_body_wrapper_even_with_nothing_to_absolutize(self):
        """Regression test for the actual production bug: bs4's lxml parser wraps whatever it's
        given in a synthetic <html><body> (readability's doc.summary() output already looks like
        a full document, so lxml has no reason to treat it as a fragment). Stripping that wrapper
        via decode_contents() must happen unconditionally - the original version of this function
        only re-serialized when it actually rewrote a URL, so an article whose links/images were
        already all absolute (common, not an edge case) leaked the wrapper straight into the
        newspaper's assembled HTML verbatim. A second <html> tag appearing mid-document is enough
        to confuse WeasyPrint's parser into silently dropping everything after it until it
        resyncs, sometimes taking an entire story down with it."""
        html = "<html><body><p>Already-absolute content, nothing to rewrite.</p></body></html>"

        result = rss._make_urls_absolute(html, "https://example.com/posts/some-article/")

        assert "<html>" not in result
        assert "<body>" not in result
        assert "Already-absolute content" in result

    def test_noop_without_body_or_base_url(self):
        assert rss._make_urls_absolute("", "https://example.com/") == ""
        assert rss._make_urls_absolute("<p>x</p>", "") == "<p>x</p>"


def test_rss_provider_strips_headline_duplicated_inside_article_body(monkeypatch):
    # Mirrors real sites (Engadget, The Register) whose article markup nests the headline as a
    # heading inside the same container readability extracts as "the article body" - without
    # stripping it, the story would render with the headline twice.
    class FakeDocument:
        def __init__(self, html):
            pass

        def title(self):
            return "Real Headline Here"

        def summary(self):
            return (
                '<div class="news-article">'
                "<h1 class=\"title-gallery\">Real Headline Here</h1>"
                "<p>The actual first paragraph of the story.</p>"
                "</div>"
            )

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[_feed_entry(summary=None)]),
    )
    monkeypatch.setattr(
        rss.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(ok=True, text="<html></html>"),
    )
    monkeypatch.setattr(rss, "Document", FakeDocument)

    provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
    stories = provider.get_stories()

    assert stories[0].headline == "Real Headline Here"
    assert "title-gallery" not in stories[0].body_html
    assert "The actual first paragraph of the story." in stories[0].body_html


class TestStripDuplicateLeadingHeading:
    def test_strips_an_exact_match(self):
        result = rss._strip_duplicate_leading_heading(
            "<h1>Same Title</h1><p>Body text.</p>", "Same Title"
        )
        assert "<h1>" not in result
        assert "Body text." in result

    def test_strips_when_nested_inside_wrapper_divs(self):
        # Engadget's actual structure: heading lives inside nested <div>s, not at the top level.
        result = rss._strip_duplicate_leading_heading(
            '<div><div class="news-article"><h1 class="title-gallery">Same Title</h1>'
            "<p>Body text.</p></div></div>",
            "Same Title",
        )
        assert "title-gallery" not in result
        assert "Body text." in result

    def test_strips_past_a_short_leading_kicker(self):
        # The Register's actual structure: a short category "kicker" precedes the heading.
        result = rss._strip_duplicate_leading_heading(
            '<p class="kicker">ai and ml</p><h1>Same Title</h1><p>Body text.</p>',
            "Same Title",
        )
        assert "<h1>" not in result
        assert "Body text." in result

    def test_strips_when_headline_has_a_site_name_suffix(self):
        # MacRumors' actual structure: doc.title() keeps the page's "<title> - MacRumors" suffix,
        # but the embedded heading itself doesn't carry it.
        result = rss._strip_duplicate_leading_heading(
            "<h1>Same Title</h1><p>Body text.</p>", "Same Title - MacRumors"
        )
        assert "<h1>" not in result
        assert "Body text." in result

    def test_leaves_a_real_leading_paragraph_alone(self):
        html = '<p>A real, substantial opening paragraph of actual body content.</p><h1>Same Title</h1>'
        assert rss._strip_duplicate_leading_heading(html, "Same Title") == html

    def test_leaves_a_non_matching_leading_heading_alone(self):
        html = "<h1>A Completely Different Heading</h1><p>Body text.</p>"
        assert rss._strip_duplicate_leading_heading(html, "Same Title") == html

    def test_leaves_a_heading_deeper_in_real_content_alone(self):
        # Even one that happens to repeat the headline verbatim - only a *leading* duplicate is
        # the known failure mode this addresses.
        html = (
            "<p>A real, substantial opening paragraph of actual body content.</p>"
            "<h2>Same Title</h2><p>More body text.</p>"
        )
        assert rss._strip_duplicate_leading_heading(html, "Same Title") == html

    def test_noop_without_a_headline_or_body(self):
        assert rss._strip_duplicate_leading_heading("<h1>X</h1>", "") == "<h1>X</h1>"
        assert rss._strip_duplicate_leading_heading("", "Same Title") == ""


def test_rss_provider_falls_back_to_feed_summary_when_readability_fails(monkeypatch):
    class BrokenDocument:
        def __init__(self, html):
            raise TypeError("boom")

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[_feed_entry()]),
    )
    monkeypatch.setattr(
        rss.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(ok=True, text="<html></html>"),
    )
    monkeypatch.setattr(rss, "Document", BrokenDocument)

    provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
    stories = provider.get_stories()

    assert stories[0].headline == "Feed title"
    assert stories[0].body_html == "<p>Feed summary</p>"
    assert stories[0].byline == "example.com"


def test_rss_provider_can_hide_all_bylines(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    title="One",
                    content=[rss.feedparser.FeedParserDict({"value": "<p>One</p>"})],
                ),
                _feed_entry(
                    title="Two",
                    content=[rss.feedparser.FeedParserDict({"value": "<p>Two</p>"})],
                ),
            ]
        ),
    )

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        byline="none",
    )
    stories = provider.get_stories()

    assert stories[0].byline is None
    assert stories[1].byline is None


def test_rss_provider_can_show_only_first_byline(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    title="One",
                    content=[rss.feedparser.FeedParserDict({"value": "<p>One</p>"})],
                ),
                _feed_entry(
                    title="Two",
                    content=[rss.feedparser.FeedParserDict({"value": "<p>Two</p>"})],
                ),
            ]
        ),
    )

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        byline="first",
    )
    stories = provider.get_stories()

    assert stories[0].byline == "example.com"
    assert stories[1].byline is None
