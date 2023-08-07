import enum
import re
import json
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
        with open(filepath, "r") as fh:
            config_dict = json.load(fh)
    except ValueError as err:
        raise ValueError(
            "Honk Honk! Syntax Error in config file {0}".format(filepath)
        ) from err
    return config_dict


def construct_story_providers_from_config_dict(config: dict):
    from goosepaper.storyprovider.rss import RSSFeedStoryProvider
    from goosepaper.storyprovider.reddit import RedditHeadlineStoryProvider
    from goosepaper.storyprovider.mastodon import MastodonStoryProvider
    from goosepaper.storyprovider.storyprovider import CustomTextStoryProvider
    from goosepaper.storyprovider.weather import OpenMeteoWeatherStoryProvider
    from goosepaper.storyprovider.wikipedia import WikipediaCurrentEventsStoryProvider

    StoryProviderConfigNames = {
        "lorem": CustomTextStoryProvider,
        "text": CustomTextStoryProvider,
        "reddit": RedditHeadlineStoryProvider,
        "weather": OpenMeteoWeatherStoryProvider,
        "mastodon": MastodonStoryProvider,
        "openmeteo_weather": OpenMeteoWeatherStoryProvider,
        "wikipedia_current_events": WikipediaCurrentEventsStoryProvider,
        "rss": RSSFeedStoryProvider,
    }

    if "stories" not in config:
        return []

    stories = []

    for provider_config in config["stories"]:
        provider_name = provider_config["provider"]
        if provider_name not in StoryProviderConfigNames:
            raise ValueError(f"Provider {provider_name} does not exist.")
        arguments = provider_config["config"] if "config" in provider_config else {}
        if arguments.get("skip"):
            continue
        else:
            stories.append(StoryProviderConfigNames[provider_name](**arguments))
    return stories
