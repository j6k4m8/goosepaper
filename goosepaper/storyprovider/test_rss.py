import time

from .rss import RSSFeedStoryProvider


class _Entry(dict):
    __getattr__ = dict.__getitem__


class _Response:
    def __init__(self, *, ok=True, text="", content=b"", encoding=None):
        self.ok = ok
        self.text = text
        self.content = content
        self.encoding = encoding


def test_rss_provider_uses_decoded_response_text(monkeypatch):
    entry = _Entry(
        title="Feed Title",
        summary="<p>Feed summary</p>",
        link="https://example.com/story",
        updated_parsed=time.gmtime(),
    )
    monkeypatch.setattr(
        "goosepaper.storyprovider.rss.feedparser.parse",
        lambda _: type(
            "Feed",
            (),
            {
                "entries": [entry]
            },
        )(),
    )
    monkeypatch.setattr(
        "goosepaper.storyprovider.rss.requests.get",
        lambda *args, **kwargs: _Response(
            ok=True,
            text=(
                "<html><head><title>Decoded Title</title></head>"
                "<body><article><p>Decoded body</p></article></body></html>"
            ),
            content=b"<html></html>",
        ),
    )

    stories = RSSFeedStoryProvider("https://example.com/feed.xml").get_stories()

    assert len(stories) == 1
    assert stories[0].headline == "Decoded Title"


def test_rss_provider_falls_back_when_readability_fails(monkeypatch):
    entry = _Entry(
        title="Feed Title",
        summary="<p>Feed summary</p>",
        link="https://example.com/story",
        updated_parsed=time.gmtime(),
    )
    monkeypatch.setattr(
        "goosepaper.storyprovider.rss.feedparser.parse",
        lambda _: type(
            "Feed",
            (),
            {
                "entries": [entry]
            },
        )(),
    )
    monkeypatch.setattr(
        "goosepaper.storyprovider.rss.requests.get",
        lambda *args, **kwargs: _Response(
            ok=True,
            text="<html><body>broken</body></html>",
            content=b"<html><body>broken</body></html>",
        ),
    )

    def _raise(_value):
        raise TypeError("boom")

    monkeypatch.setattr("goosepaper.storyprovider.rss.Document", _raise)

    stories = RSSFeedStoryProvider("https://example.com/feed.xml").get_stories()

    assert len(stories) == 1
    assert stories[0].headline == "Feed Title"
    assert stories[0].body_html == "<p>Feed summary</p>"
