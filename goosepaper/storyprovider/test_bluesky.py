from . import bluesky


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _feed_item(
    *,
    text="Hello from Bluesky",
    created_at="2026-04-24T15:30:00Z",
    handle="jordan.matelsky.com",
    display_name="Jordan Matelsky",
    reason=None,
):
    item = {
        "post": {
            "author": {
                "handle": handle,
                "displayName": display_name,
            },
            "record": {
                "text": text,
                "createdAt": created_at,
            },
        }
    }
    if reason is not None:
        item["reason"] = reason
    return item


def test_bluesky_provider_uses_public_author_feed(monkeypatch):
    seen = {}

    def fake_get(url, *, params, headers, timeout):
        seen["url"] = url
        seen["params"] = params
        seen["headers"] = headers
        seen["timeout"] = timeout
        return _FakeResponse({"feed": [_feed_item(text="Hello\nworld")]})

    monkeypatch.setattr(bluesky.requests, "get", fake_get)

    provider = bluesky.BlueskyStoryProvider("jordan.matelsky.com", limit=4)
    stories = provider.get_stories(limit=2)

    assert seen["url"] == "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
    assert seen["params"] == {
        "actor": "jordan.matelsky.com",
        "filter": "posts_with_replies",
        "limit": 2,
    }
    assert seen["timeout"] == 20
    assert seen["headers"]["User-Agent"].startswith("goosepaper/")
    assert len(stories) == 1
    assert stories[0].headline == "Jordan Matelsky at 2026-04-24 15:30"
    assert stories[0].byline == "@jordan.matelsky.com"
    assert stories[0].body_html == "<p>Hello<br />world</p>"


def test_bluesky_provider_skips_reposts(monkeypatch):
    monkeypatch.setattr(
        bluesky.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(
            {
                "feed": [
                    _feed_item(
                        text="A reposted post",
                        reason={"$type": "app.bsky.feed.defs#reasonRepost"},
                    ),
                    _feed_item(text="An original post"),
                ]
            }
        ),
    )

    provider = bluesky.BlueskyStoryProvider("jordan.matelsky.com")
    stories = provider.get_stories(limit=5)

    assert len(stories) == 1
    assert stories[0].body_html == "<p>An original post</p>"


def test_bluesky_provider_honors_since_days_ago(monkeypatch):
    monkeypatch.setattr(
        bluesky.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(
            {
                "feed": [
                    _feed_item(
                        text="Old post",
                        created_at="2020-01-01T00:00:00Z",
                    ),
                    _feed_item(
                        text="Recent post",
                        created_at="2026-04-24T15:30:00Z",
                    ),
                ]
            }
        ),
    )

    provider = bluesky.BlueskyStoryProvider(
        "infinitescream.bsky.social",
        since_days_ago=30,
    )
    stories = provider.get_stories(limit=5)

    assert len(stories) == 1
    assert stories[0].body_html == "<p>Recent post</p>"
