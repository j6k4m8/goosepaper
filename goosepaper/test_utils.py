from .util import (
    htmlize,
    clean_html,
    clean_text,
    construct_story_providers_from_config_dict,
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
        {"stories": [{"provider": "twitter", "config": {"usernames": "j6m8"}}]}
    )
    assert len(stories) == 1

    stories = construct_story_providers_from_config_dict(
        {
            "stories": [
                {"provider": "twitter", "config": {"usernames": ["j6m8"]}},
                {"provider": "reddit", "config": {"subreddit": "worldnews"}},
            ]
        }
    )
    assert len(stories) == 2
