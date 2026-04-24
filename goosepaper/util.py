import enum
import importlib
import json
import re
from typing import List, Union


def htmlize(text: Union[str, List[str]]) -> str:
    """
    Generate HTML text from a text string, correctly formatting paragraphs etc.
    """
    # TODO:
    #   * Escaping
    #   * Paragraph delims
    #   * Remove illegal elements
    if isinstance(text, list):
        return "".join([f"<p>{line}</p>" for line in text])
    return f"<p>{text}</p>"


def clean_html(html: str) -> str:
    html = html.replace("â€TM", "'")
    html = re.sub(r"http[s]?:\/\/[^\s\"']+", "", html)
    return html


def clean_text(text: str) -> str:
    text = text.replace("â€TM", "'")
    text = re.sub(r"http[s]?:\/\/[^\s\"']+", "", text)
    return text


class PlacementPreference(enum.Enum):
    NONE = 0
    FULLPAGE = 1
    SIDEBAR = 2
    EAR = 3
    FOLIO = 4
    BANNER = 5


class StoryPriority(enum.Enum):
    DEFAULT = 0
    LOW = 1
    HEADLINE = 5
    BANNER = 9


def load_config_file(filepath: str) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            config_dict = json.load(fh)
    except ValueError as err:
        raise ValueError(
            "Honk Honk! Syntax Error in config file {0}".format(filepath)
        ) from err
    return config_dict


def construct_story_providers_from_config_dict(config: dict):
    if "sources" not in config:
        return []
    return construct_story_providers_from_source_configs(config["sources"])


def construct_story_providers_from_source_configs(source_configs):
    provider_specs = {
        "text": (
            "goosepaper.storyprovider.storyprovider",
            "CustomTextStoryProvider",
            lambda options: dict(options),
        ),
        "reddit": (
            "goosepaper.storyprovider.reddit",
            "RedditHeadlineStoryProvider",
            lambda options: dict(options),
        ),
        "rss": (
            "goosepaper.storyprovider.rss",
            "RSSFeedStoryProvider",
            lambda options: {
                "rss_path": options["url"],
                **{
                    key: value
                    for key, value in options.items()
                    if key in {
                        "limit",
                        "since_days_ago",
                        "byline",
                        "body_source",
                    }
                },
            },
        ),
        "mastodon": (
            "goosepaper.storyprovider.mastodon",
            "MastodonStoryProvider",
            lambda options: dict(options),
        ),
        "bluesky": (
            "goosepaper.storyprovider.bluesky",
            "BlueskyStoryProvider",
            lambda options: dict(options),
        ),
        "weather": (
            "goosepaper.storyprovider.weather",
            "OpenMeteoWeatherStoryProvider",
            lambda options: {
                "lat": options["lat"],
                "lon": options["lon"],
                "F": options.get("unit", "F") == "F",
                **(
                    {"timezone": options["timezone"]}
                    if "timezone" in options
                    else {}
                ),
            },
        ),
        "wikipedia": (
            "goosepaper.storyprovider.wikipedia",
            "WikipediaCurrentEventsStoryProvider",
            lambda options: {},
        ),
    }

    stories = []

    for source_config in source_configs:
        source_type, options = _source_config_parts(source_config)
        if source_type not in provider_specs:
            raise ValueError(f"Source type {source_type} does not exist.")
        module_name, class_name, normalize = provider_specs[source_type]
        module = importlib.import_module(module_name)
        provider_class = getattr(module, class_name)
        stories.append(provider_class(**normalize(options)))
    return stories


def _source_config_parts(source_config):
    if hasattr(source_config, "type") and hasattr(source_config, "options"):
        return source_config.type, dict(source_config.options)
    if not isinstance(source_config, dict):
        raise ValueError("Each source must be a dict-like object.")
    if "type" not in source_config:
        raise ValueError("Each source must include a type.")
    return source_config["type"], {
        key: value for key, value in source_config.items() if key != "type"
    }
