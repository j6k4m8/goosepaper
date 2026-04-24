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
    ):
        self.ok = ok
        self.text = text
        self.content = content
        self.encoding = encoding


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
    stories = provider.get_stories(limit=1)

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
    stories = provider.get_stories(limit=1)

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
    stories = provider.get_stories(limit=1)

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
    stories = provider.get_stories(limit=1)

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
    stories = provider.get_stories(limit=1)

    assert isinstance(seen["html"], str)
    assert stories[0].headline == "Readable title"
    assert stories[0].body_html == "<p>Readable summary</p>"


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
    stories = provider.get_stories(limit=1)

    assert seen["requests"] == 1
    assert stories[0].headline == "Readable title"
    assert stories[0].body_html == "<p>Readable summary</p>"


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
    stories = provider.get_stories(limit=1)

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
    stories = provider.get_stories(limit=2)

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
    stories = provider.get_stories(limit=2)

    assert stories[0].byline == "example.com"
    assert stories[1].byline is None
