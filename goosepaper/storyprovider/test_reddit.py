import datetime
from types import SimpleNamespace

from . import reddit
from ..util import PlacementPreference


def _updated_parsed(*, days_ago=0, hours_ago=0):
    delta = datetime.timedelta(days=days_ago, hours=hours_ago)
    return (
        (datetime.datetime.now() - delta)
        .replace(microsecond=0)
        .timetuple()
    )


def _feed_entry(
    *,
    title="A reddit post",
    author="redditor",
    link="https://www.reddit.com/r/news/comments/post/a_reddit_post/",
    updated_parsed=None,
):
    if updated_parsed is None:
        updated_parsed = _updated_parsed(days_ago=1)
    return SimpleNamespace(
        title=title,
        author=author,
        link=link,
        updated_parsed=updated_parsed,
    )


class _FakeResponse:
    def __init__(
        self,
        *,
        content=b"<feed></feed>",
        status_code=200,
        headers=None,
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise reddit.requests.HTTPError(
                f"{self.status_code} Client Error",
                response=self,
            )
        return None


def test_reddit_provider_fetches_feed_with_requests(monkeypatch):
    seen = {}

    def fake_get(url, *, params, headers, timeout):
        seen["url"] = url
        seen["params"] = params
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
    stories = provider.get_stories()

    assert seen["url"] == "https://www.reddit.com/r/news.rss"
    assert seen["params"] == {"limit": 3}
    assert seen["timeout"] == 20
    assert seen["headers"]["User-Agent"].startswith("python:goosepaper:")
    assert "github.com/j6k4m8/goosepaper" in seen["headers"]["User-Agent"]
    assert len(stories) == 1
    assert stories[0].plain_text() == "Top story"
    assert stories[0].byline == "poster in r/news"
    assert stories[0].placement_preference == PlacementPreference.SIDEBAR
    assert stories[0].section_title == "Reddit"
    assert stories[0].short_form is True


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
                    updated_parsed=_updated_parsed(days_ago=365),
                ),
                _feed_entry(
                    title="Recent story",
                    updated_parsed=_updated_parsed(days_ago=1),
                ),
            ]
        ),
    )

    provider = reddit.RedditHeadlineStoryProvider("news", since_days_ago=30)
    stories = provider.get_stories()

    assert len(stories) == 1
    assert stories[0].plain_text() == "Recent story"
    assert stories[0].section_title == "Reddit"


def test_reddit_provider_retries_after_rate_limit(monkeypatch):
    calls = []
    sleeps = []
    responses = [
        _FakeResponse(
            status_code=429,
            headers={"x-ratelimit-reset": "4"},
        ),
        _FakeResponse(content=b"<feed>reddit</feed>"),
    ]

    def fake_get(url, *, params, headers, timeout):
        calls.append((url, params))
        return responses.pop(0)

    monkeypatch.setattr(reddit.requests, "get", fake_get)
    monkeypatch.setattr(
        reddit.time,
        "sleep",
        lambda seconds: sleeps.append(seconds),
    )
    monkeypatch.setattr(
        reddit.feedparser,
        "parse",
        lambda payload: SimpleNamespace(
            entries=[_feed_entry(title="Retried")]
        ),
    )

    provider = reddit.RedditHeadlineStoryProvider(
        "todayilearned",
        limit=5,
        max_retries=1,
    )
    stories = provider.get_stories()

    assert calls == [
        ("https://www.reddit.com/r/todayilearned.rss", {"limit": 5}),
        ("https://www.reddit.com/r/todayilearned.rss", {"limit": 5}),
    ]
    assert sleeps == [4.0]
    assert len(stories) == 1
    assert stories[0].plain_text() == "Retried"


def test_reddit_provider_supports_combined_subreddit_feed(monkeypatch):
    seen = {}

    def fake_get(url, *, params, headers, timeout):
        seen["url"] = url
        seen["params"] = params
        return _FakeResponse(content=b"<feed>reddit</feed>")

    monkeypatch.setattr(reddit.requests, "get", fake_get)
    monkeypatch.setattr(
        reddit.feedparser,
        "parse",
        lambda payload: SimpleNamespace(
            entries=[
                _feed_entry(
                    title="TIL post",
                    author="tilposter",
                    link=(
                        "https://www.reddit.com/r/todayilearned/"
                        "comments/post/til_post/"
                    ),
                ),
                _feed_entry(
                    title="News post",
                    author="newsposter",
                    link=(
                        "https://www.reddit.com/r/news/"
                        "comments/post/news_post/"
                    ),
                ),
            ]
        ),
    )

    provider = reddit.RedditHeadlineStoryProvider(
        "news+todayilearned",
        limit=2,
    )
    stories = provider.get_stories()

    assert provider.subreddits == ["news", "todayilearned"]
    assert seen["url"] == "https://www.reddit.com/r/news+todayilearned.rss"
    assert seen["params"] == {"limit": 2}
    assert [story.plain_text() for story in stories] == [
        "TIL post",
        "News post",
    ]
    assert [story.byline for story in stories] == [
        "tilposter in r/todayilearned",
        "newsposter in r/news",
    ]


def test_reddit_provider_can_group_combined_feed_by_subreddit(monkeypatch):
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
                    title="TIL post",
                    link=(
                        "https://www.reddit.com/r/todayilearned/"
                        "comments/post/til_post/"
                    ),
                ),
                _feed_entry(
                    title="News post",
                    link=(
                        "https://www.reddit.com/r/news/"
                        "comments/post/news_post/"
                    ),
                ),
            ]
        ),
    )

    provider = reddit.RedditHeadlineStoryProvider(
        "news+todayilearned",
        limit=2,
        multi_sub_order="subreddit",
    )
    stories = provider.get_stories()

    assert [story.plain_text() for story in stories] == [
        "News post",
        "TIL post",
    ]
