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
