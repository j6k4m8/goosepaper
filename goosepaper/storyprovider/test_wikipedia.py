from . import wikipedia


def test_empty_feed_returns_no_stories_instead_of_crashing(monkeypatch):
    """A transient network hiccup (or the upstream feed briefly returning zero entries) should
    degrade to "no story this run", the same way other providers handle an empty feed - not an
    unhandled IndexError out of feed.entries[0]."""
    monkeypatch.setattr(
        wikipedia.feedparser, "parse", lambda *a, **kw: wikipedia.feedparser.FeedParserDict(entries=[])
    )

    stories = wikipedia.WikipediaCurrentEventsStoryProvider().get_stories()

    assert stories == []
