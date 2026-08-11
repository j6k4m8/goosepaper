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
        html = '<img src="https://cdn.example.com/foo.jpg">'

        result = rss._make_urls_absolute(html, "https://example.com/story/")

        assert result == html

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

        assert result == html

    def test_does_not_leak_a_synthetic_body_wrapper(self):
        html = '<p>hello</p><img src="/foo.jpg">'

        result = rss._make_urls_absolute(html, "https://example.com/")

        assert result == '<p>hello</p><img src="https://example.com/foo.jpg"/>'

    def test_noop_when_nothing_needed_absolutizing(self):
        html = "<p>plain text, no urls here</p>"

        result = rss._make_urls_absolute(html, "https://example.com/story/")

        assert result is html

    def test_noop_without_body_or_base_url(self):
        assert rss._make_urls_absolute("", "https://example.com/") == ""
        assert rss._make_urls_absolute("<p>x</p>", "") == "<p>x</p>"


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
