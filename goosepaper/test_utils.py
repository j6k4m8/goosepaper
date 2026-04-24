from .util import (
    clean_text,
    clean_html,
    construct_story_providers_from_source_configs,
    construct_story_providers_from_config_dict,
    htmlize,
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
