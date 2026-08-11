from .util import (
    clean_text,
    clean_html,
    construct_story_providers_from_source_configs,
    construct_story_providers_from_config_dict,
    htmlize,
    register_story_provider,
)


def test_htmlize():
    assert htmlize(["foo", "bar"]) == "<p>foo</p><p>bar</p>"


def test_clean_html():
    assert clean_html("fooâ€TMbar") == "foo'bar"


def test_clean_text():
    assert clean_text("fooâ€TMbar") == "foo'bar"


def test_construct_story_providers_from_config_dict():
    assert construct_story_providers_from_config_dict({}) == []
    stories = construct_story_providers_from_config_dict(
        {
            "sources": [
                {
                    "type": "text",
                    "headline": "hello",
                    "text": "world",
                }
            ]
        }
    )
    assert len(stories) == 1
    assert stories[0].headline == "hello"

    stories = construct_story_providers_from_source_configs(
        [
            {
                "type": "text",
                "headline": "One",
            },
            {
                "type": "text",
                "headline": "Two",
            },
        ]
    )
    assert len(stories) == 2


def test_register_story_provider_makes_a_custom_type_constructable():
    class _DummyProvider:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_stories(self, limit: int = 1):
            return []

    register_story_provider(
        "dummy_test_provider", _DummyProvider, required={"handle"}, optional={"limit"}
    )
    stories = construct_story_providers_from_source_configs(
        [{"type": "dummy_test_provider", "handle": "goose", "limit": 3}]
    )
    assert len(stories) == 1
    assert isinstance(stories[0], _DummyProvider)
    assert stories[0].kwargs == {"handle": "goose", "limit": 3}


def test_construct_story_providers_passes_rss_byline_option():
    stories = construct_story_providers_from_source_configs(
        [
            {
                "type": "rss",
                "url": "https://example.com/feed.xml",
                "byline": "first",
                "body_source": "summary",
            }
        ]
    )

    assert stories[0].byline_mode == "first"
    assert stories[0].body_source == "summary"


def test_construct_story_providers_supports_bluesky():
    stories = construct_story_providers_from_source_configs(
        [
            {
                "type": "bluesky",
                "username": "jordan.matelsky.com",
                "include_replies": False,
            }
        ]
    )

    assert stories[0].username == "jordan.matelsky.com"
    assert stories[0].include_replies is False
    assert stories[0].feed_filter == "posts_no_replies"


def test_construct_story_providers_supports_readwise(monkeypatch):
    monkeypatch.setenv("GOOSEPAPER_TEST_READWISE_TOKEN", "test-token")

    stories = construct_story_providers_from_source_configs(
        [
            {
                "type": "readwise",
                "token_env": "GOOSEPAPER_TEST_READWISE_TOKEN",
                "limit": 3,
                "location": "new",
                "category": "rss",
                "tags": ["daily"],
                "body_source": "text",
            }
        ]
    )

    assert stories[0].token == "test-token"
    assert stories[0].limit == 3
    assert stories[0].location == "new"
    assert stories[0].category == "rss"
    assert stories[0].tags == ["daily"]
    assert stories[0].body_source == "text"


def test_construct_story_providers_passes_weather_breakdown_options():
    stories = construct_story_providers_from_source_configs(
        [
            {
                "type": "weather",
                "lat": 36.5,
                "lon": -75.1,
                "mode": "hourly",
                "hours": 12,
                "step_hours": 4,
                "clock_format": "24h",
                "timezone": "America/New_York",
            }
        ]
    )

    assert stories[0].mode == "hourly"
    assert stories[0].hours == 12
    assert stories[0].step_hours == 4
    assert stories[0].clock_format == "24h"
    assert stories[0].timezone == "America/New_York"


def test_construct_story_providers_passes_combined_weather_mode():
    stories = construct_story_providers_from_source_configs(
        [
            {
                "type": "weather",
                "lat": 36.5,
                "lon": -75.1,
                "mode": "hourly_daily",
                "hours": 12,
                "step_hours": 4,
                "days": 4,
            }
        ]
    )

    assert stories[0].mode == "hourly_daily"
    assert stories[0].days == 4


def test_construct_story_providers_passes_comic_type_option():
    stories = construct_story_providers_from_source_configs(
        [{"type": "comic", "comic_type": "gocomics", "comic_name": "garfield"}]
    )

    assert stories[0].comic_type == "gocomics"
    assert stories[0].comic_name == "garfield"
