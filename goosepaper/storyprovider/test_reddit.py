import datetime
from types import SimpleNamespace

from . import reddit
from ..util import PlacementPreference


def _feed_entry(
    *,
    title="A reddit post",
    author="redditor",
    updated_parsed=None,
):
    if updated_parsed is None:
        updated_parsed = datetime.datetime(
            2026,
            4,
            24,
            10,
            30,
            0,
        ).timetuple()
    return SimpleNamespace(
        title=title,
        author=author,
        updated_parsed=updated_parsed,
    )


class _FakeResponse:
    def __init__(self, *, content=b"<feed></feed>"):
        self.content = content

    def raise_for_status(self):
        return None


def test_reddit_provider_fetches_feed_with_requests_and_user_agent(monkeypatch):
    seen = {}

    def fake_get(url, *, headers, timeout):
        seen["url"] = url
        seen["headers"] = headers
        seen["timeout"] = timeout
        return _FakeResponse(content=b"<feed>reddit</feed>")

    monkeypatch.setattr(reddit.requests, "get", fake_get)
    monkeypatch.setattr(
        reddit.feedparser,
        "parse",
        lambda payload: SimpleNamespace(
            entries=[_feed_entry(title="Top story", author="poster")]
        ),
    )

    provider = reddit.RedditHeadlineStoryProvider("/r/news", limit=3)
    stories = provider.get_stories(limit=2)

    assert seen["url"] == "https://www.reddit.com/r/news.rss"
    assert seen["timeout"] == 20
    assert seen["headers"]["User-Agent"].startswith("goosepaper/")
    assert len(stories) == 1
    assert stories[0].plain_text() == "Top story"
    assert stories[0].byline == "poster in r/news"
    assert stories[0].placement_preference == PlacementPreference.SIDEBAR


def test_reddit_provider_filters_old_entries(monkeypatch):
    monkeypatch.setattr(
        reddit.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(content=b"<feed>reddit</feed>"),
    )
    monkeypatch.setattr(
        reddit.feedparser,
        "parse",
        lambda payload: SimpleNamespace(
            entries=[
                _feed_entry(
                    title="Old story",
                    updated_parsed=datetime.datetime(
                        2020,
                        1,
                        1,
                        0,
                        0,
                        0,
                    ).timetuple(),
                ),
                _feed_entry(title="Recent story"),
            ]
        ),
    )

    provider = reddit.RedditHeadlineStoryProvider("news", since_days_ago=30)
    stories = provider.get_stories(limit=5)

    assert len(stories) == 1
    assert stories[0].plain_text() == "Recent story"
