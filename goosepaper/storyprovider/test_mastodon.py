from .mastodon import MastodonStoryProvider


def test_can_get_mastodon_stories():
    LIMIT = 5
    stories = MastodonStoryProvider(
        "https://neuromatch.social",
        "jordan",
        limit=LIMIT,
    ).get_stories()
    assert len(stories) == LIMIT
