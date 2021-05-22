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
        print("Honk Honk! Syntax Error in config file {0}".format(filepath))
        exit(1)
    return config_dict


def construct_story_providers_from_config_dict(config: dict):

    from goosepaper.rss import RSSFeedStoryProvider
    from goosepaper.twitter import MultiTwitterStoryProvider
    from goosepaper.reddit import RedditHeadlineStoryProvider
    from goosepaper.weather import WeatherStoryProvider
    from goosepaper.wikipedia import WikipediaCurrentEventsStoryProvider

    StoryProviderConfigNames = {
        "twitter": MultiTwitterStoryProvider,
        "reddit": RedditHeadlineStoryProvider,
        "weather": WeatherStoryProvider,
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
        if provider_config["config"].get("skip") == True:
            continue
        else:
            stories.append(
                StoryProviderConfigNames[provider_name](**provider_config["config"])
            )
    return stories
