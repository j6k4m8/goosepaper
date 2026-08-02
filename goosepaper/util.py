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
    UTILITY = 6
    APPENDIX = 7


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


_REGISTERED_STORY_PROVIDERS = {}


def register_story_provider(
    source_type, provider, *, required=None, optional=None, normalize=None
):
    """Register a StoryProvider so it can be used from a config file (and the CLI)
    via ``{"type": source_type, ...}``, the same way the built-in providers are.

    Args:
        source_type: the string used as a source ``"type"`` in a config.
        provider: the StoryProvider class, or a ``"module.path:ClassName"`` string
            that is imported lazily the first time the type is used.
        required: config field names that must be present for this source.
        optional: config field names that may be present.
        normalize: maps the source's config options to the provider's constructor
            kwargs; defaults to passing the options through unchanged.
    """
    _REGISTERED_STORY_PROVIDERS[source_type] = {
        "provider": provider,
        "required": set(required or ()),
        "optional": set(optional or ()),
        "normalize": normalize or (lambda options: dict(options)),
    }


def registered_story_providers():
    """The registry of externally-registered providers (see register_story_provider)."""
    return _REGISTERED_STORY_PROVIDERS


def _resolve_provider(provider):
    if isinstance(provider, str):
        module_name, _, class_name = provider.replace(":", ".").rpartition(".")
        return getattr(importlib.import_module(module_name), class_name)
    return provider


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
        "readwise": (
            "goosepaper.storyprovider.readwise",
            "ReadwiseReaderStoryProvider",
            lambda options: dict(options),
        ),
        "weather": (
            "goosepaper.storyprovider.weather",
            "OpenMeteoWeatherStoryProvider",
            lambda options: {
                "lat": options["lat"],
                "lon": options["lon"],
                "F": options.get("unit", "F") == "F",
                **({"mode": options["mode"]} if "mode" in options else {}),
                **({"hours": options["hours"]} if "hours" in options else {}),
                **(
                    {"step_hours": options["step_hours"]}
                    if "step_hours" in options
                    else {}
                ),
                **({"days": options["days"]} if "days" in options else {}),
                **(
                    {"clock_format": options["clock_format"]}
                    if "clock_format" in options
                    else {}
                ),
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
        "comic": (
            "goosepaper.storyprovider.comic",
            "DailyComicStoryProvider",
            lambda options: {"comic_type": options["comic_type"]},
        ),
    }

    stories = []

    for source_config in source_configs:
        source_type, options = _source_config_parts(source_config)
        if source_type in provider_specs:
            module_name, class_name, normalize = provider_specs[source_type]
            module = importlib.import_module(module_name)
            provider_class = getattr(module, class_name)
            stories.append(provider_class(**normalize(options)))
        elif source_type in _REGISTERED_STORY_PROVIDERS:
            spec = _REGISTERED_STORY_PROVIDERS[source_type]
            provider_class = _resolve_provider(spec["provider"])
            stories.append(provider_class(**spec["normalize"](options)))
        else:
            raise ValueError(f"Source type {source_type} does not exist.")
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
