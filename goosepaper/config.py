import argparse
import datetime
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from goosepaper.layout import LAYOUT_CHOICES
from goosepaper.styles import PAGE_PROFILE_CHOICES
from goosepaper.util import load_config_file


CONFIG_VERSION = 2
DEFAULT_PAPER_CONFIG_FILENAME = "goosepaper.json"
REPLACE_MODES = ("never", "exact", "nocase")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class PaperSettings:
    title: Optional[str] = None
    subtitle: Optional[str] = None
    style: str = "FifthAvenue"
    font_size: int = 14
    body_font: Optional[str] = None
    table_of_contents: bool = False
    layout: str = "auto"
    page_profile: str = "remarkable2"

    def __post_init__(self):
        if self.title is not None and not isinstance(self.title, str):
            raise ValueError("Paper title must be a string or null.")
        if self.subtitle is not None and not isinstance(self.subtitle, str):
            raise ValueError("Paper subtitle must be a string or null.")
        if not isinstance(self.style, str) or not self.style:
            raise ValueError("Paper style must be a non-empty string.")
        if (
            not isinstance(self.font_size, int)
            or isinstance(self.font_size, bool)
            or self.font_size <= 0
        ):
            raise ValueError("Paper font_size must be a positive integer.")
        if self.body_font is not None and (
            not isinstance(self.body_font, str) or not self.body_font.strip()
        ):
            raise ValueError("Paper body_font must be a non-empty string or null.")
        if not isinstance(self.table_of_contents, bool):
            raise ValueError("Paper table_of_contents must be a boolean.")
        if self.layout not in LAYOUT_CHOICES:
            raise ValueError(
                "Paper layout must be one of: "
                + ", ".join(f'"{layout}"' for layout in LAYOUT_CHOICES)
                + "."
            )
        if self.page_profile not in PAGE_PROFILE_CHOICES:
            raise ValueError(
                "Paper page_profile must be one of: "
                + ", ".join(f'"{profile}"' for profile in PAGE_PROFILE_CHOICES)
                + "."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "style": self.style,
            "font_size": self.font_size,
            "body_font": self.body_font,
            "table_of_contents": self.table_of_contents,
            "layout": self.layout,
            "page_profile": self.page_profile,
        }


@dataclass(frozen=True)
class DeliveryIntent:
    folder: Optional[str] = None

    def __post_init__(self):
        _validate_folder(self.folder, "delivery folder")

    def to_dict(self) -> Dict[str, Any]:
        return {"folder": self.folder}


@dataclass(frozen=True)
class DeliverySettings:
    folder: Optional[str] = None
    replace_mode: str = "never"
    cleanup: bool = False

    def __post_init__(self):
        _validate_folder(self.folder, "delivery folder")
        if self.replace_mode not in REPLACE_MODES:
            raise ValueError(
                "replace_mode must be one of: "
                + ", ".join(f'"{mode}"' for mode in REPLACE_MODES)
                + "."
            )
        if not isinstance(self.cleanup, bool):
            raise ValueError("cleanup must be a boolean.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "folder": self.folder,
            "replace_mode": self.replace_mode,
            "cleanup": self.cleanup,
        }


@dataclass(frozen=True)
class SourceConfig:
    type: str
    options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.type, str) or not self.type:
            raise ValueError("Each source must have a non-empty string type.")
        if not isinstance(self.options, dict):
            raise ValueError("Each source options payload must be an object.")

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, **self.options}


@dataclass(frozen=True)
class PaperConfig:
    version: int = CONFIG_VERSION
    paper: PaperSettings = field(default_factory=PaperSettings)
    sources: List[SourceConfig] = field(default_factory=list)
    delivery: DeliveryIntent = field(default_factory=DeliveryIntent)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "paper": self.paper.to_dict(),
            "sources": [source.to_dict() for source in self.sources],
            "delivery": self.delivery.to_dict(),
        }


@dataclass(frozen=True)
class UserConfig:
    version: int = CONFIG_VERSION
    delivery_defaults: DeliverySettings = field(default_factory=DeliverySettings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "delivery_defaults": self.delivery_defaults.to_dict(),
        }


@dataclass(frozen=True)
class ResolvedConfig:
    paper: PaperSettings
    sources: List[SourceConfig]
    delivery: DeliverySettings
    output: str
    deliver: bool
    nostory: bool
    showconfig: bool
    paper_config_path: Optional[Path]
    user_config_path: Path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_config_path": (
                str(self.paper_config_path) if self.paper_config_path else None
            ),
            "user_config_path": str(self.user_config_path),
            "paper": self.paper.to_dict(),
            "sources": [source.to_dict() for source in self.sources],
            "delivery": self.delivery.to_dict(),
            "output": self.output,
            "deliver": self.deliver,
            "nostory": self.nostory,
            "showconfig": self.showconfig,
        }


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="goosepaper",
        description="Goosepaper generates and optionally delivers a daily newspaper.",
    )
    parser.add_argument(
        "-c",
        "--config",
        required=False,
        help="The paper config file to use. Defaults to ./goosepaper.json.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        help="The output file path at which to save the paper.",
    )
    parser.add_argument(
        "--deliver",
        action="store_true",
        required=False,
        help="Deliver the output file to your reMarkable after rendering.",
    )
    parser.add_argument(
        "-f",
        "--folder",
        required=False,
        help="Override the delivery folder for this run.",
    )
    parser.add_argument(
        "--replace-mode",
        choices=REPLACE_MODES,
        required=False,
        help='How to handle delivery collisions: "never", "exact", or "nocase".',
    )
    cleanup_group = parser.add_mutually_exclusive_group()
    cleanup_group.add_argument(
        "--cleanup",
        dest="cleanup",
        action="store_true",
        default=None,
        help="Delete the output file after a successful delivery.",
    )
    cleanup_group.add_argument(
        "--no-cleanup",
        dest="cleanup",
        action="store_false",
        default=None,
        help="Keep the output file after delivery, even if user defaults say otherwise.",
    )
    parser.add_argument(
        "-n",
        "--nostory",
        required=False,
        default=False,
        action="store_true",
        help="Skip story creation. Combined with '--deliver' this uploads a pre-existing output file.",
    )
    parser.add_argument(
        "--showconfig",
        action="store_true",
        required=False,
        help="Print the resolved configuration for this run.",
    )
    return parser


def default_paper_config_path() -> Path:
    return Path.cwd() / DEFAULT_PAPER_CONFIG_FILENAME


def default_user_config_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    base = (
        Path(xdg_config_home).expanduser()
        if xdg_config_home
        else Path.home() / ".config"
    )
    return base / "goosepaper" / "config.json"


def load_paper_config(path: Path) -> PaperConfig:
    raw = _load_json_object(path, "paper config")
    _maybe_raise_legacy_paper_config_error(raw)
    _require_config_version(raw, "paper config")
    _reject_unknown_keys(raw, {"version", "paper", "sources", "delivery"}, "paper config")

    try:
        return PaperConfig(
            version=CONFIG_VERSION,
            paper=_parse_paper_settings(raw.get("paper", {})),
            sources=_parse_sources(raw.get("sources", [])),
            delivery=_parse_delivery_intent(raw.get("delivery", {})),
        )
    except ValueError as err:
        raise ConfigError(str(err)) from err


def load_user_config(path: Optional[Path] = None) -> UserConfig:
    config_path = path or default_user_config_path()
    try:
        raw = _load_json_object(config_path, "user config")
    except FileNotFoundError:
        return UserConfig()

    _maybe_raise_legacy_user_config_error(raw)
    _require_config_version(raw, "user config")
    _reject_unknown_keys(raw, {"version", "delivery_defaults"}, "user config")

    try:
        return UserConfig(
            version=CONFIG_VERSION,
            delivery_defaults=_parse_delivery_settings(
                raw.get("delivery_defaults", {}), "delivery_defaults"
            ),
        )
    except ValueError as err:
        raise ConfigError(str(err)) from err


def resolve_runtime_config(args: Optional[Sequence[str]] = None) -> ResolvedConfig:
    cli_args = build_cli_parser().parse_args(args)

    if not cli_args.deliver and _has_delivery_cli_overrides(cli_args):
        raise ConfigError(
            "Delivery override flags require '--deliver'. "
            "Run goosepaper with '--deliver' to use '--folder', '--replace-mode', or cleanup overrides."
        )

    if cli_args.nostory and not cli_args.deliver:
        raise ConfigError(
            "'--nostory' only makes sense together with '--deliver'. "
            "Otherwise goosepaper has nothing to do."
        )

    if cli_args.nostory and not cli_args.output:
        raise ConfigError(
            "'--nostory' requires '--output' so goosepaper knows which existing file to deliver."
        )

    paper_config_path = _resolve_paper_config_path(cli_args.config)
    paper_config = PaperConfig()
    if paper_config_path is not None:
        paper_config = load_paper_config(paper_config_path)
    elif not cli_args.nostory:
        raise ConfigError(
            "No paper config found. Create ./goosepaper.json or pass '--config /path/to/paper.json'."
        )

    should_load_user_config = (
        cli_args.deliver
        or cli_args.showconfig
        or _has_delivery_cli_overrides(cli_args)
    )
    user_config = load_user_config() if should_load_user_config else UserConfig()

    return ResolvedConfig(
        paper=paper_config.paper,
        sources=paper_config.sources,
        delivery=resolve_delivery_settings(
            user_defaults=user_config.delivery_defaults,
            paper_delivery=paper_config.delivery,
            folder_override=cli_args.folder,
            replace_mode_override=cli_args.replace_mode,
            cleanup_override=cli_args.cleanup,
        ),
        output=cli_args.output or default_output_filename(),
        deliver=cli_args.deliver,
        nostory=cli_args.nostory,
        showconfig=cli_args.showconfig,
        paper_config_path=paper_config_path,
        user_config_path=default_user_config_path(),
    )


def resolve_delivery_settings(
    user_defaults: Optional[DeliverySettings] = None,
    paper_delivery: Optional[DeliveryIntent] = None,
    folder_override: Optional[str] = None,
    replace_mode_override: Optional[str] = None,
    cleanup_override: Optional[bool] = None,
) -> DeliverySettings:
    user_defaults = user_defaults or DeliverySettings()
    paper_delivery = paper_delivery or DeliveryIntent()
    try:
        return DeliverySettings(
            folder=(
                folder_override
                if folder_override is not None
                else (
                    paper_delivery.folder
                    if paper_delivery.folder is not None
                    else user_defaults.folder
                )
            ),
            replace_mode=replace_mode_override or user_defaults.replace_mode,
            cleanup=user_defaults.cleanup
            if cleanup_override is None
            else cleanup_override,
        )
    except ValueError as err:
        raise ConfigError(str(err)) from err


def default_output_filename() -> str:
    return f"Goosepaper-{datetime.datetime.now().strftime('%Y-%B-%d-%H-%M')}.pdf"


def dump_resolved_config(config: ResolvedConfig) -> str:
    return json.dumps(config.to_dict(), indent=2)


def _resolve_paper_config_path(config_argument: Optional[str]) -> Optional[Path]:
    if config_argument:
        config_path = Path(config_argument).expanduser()
        if not config_path.is_file():
            raise ConfigError(
                f"Couldn't find paper config file ({config_argument})."
            )
        return config_path.resolve()

    default_path = default_paper_config_path()
    if default_path.is_file():
        return default_path.resolve()
    return None


def _load_json_object(path: Path, config_kind: str) -> Dict[str, Any]:
    try:
        raw = load_config_file(str(path))
    except FileNotFoundError:
        raise
    except ValueError as err:
        raise ConfigError(f"Honk! Invalid JSON in {config_kind} {path}.") from err

    if not isinstance(raw, dict):
        raise ConfigError(
            f"The {config_kind} at {path} must contain a JSON object at the top level."
        )
    return raw


def _maybe_raise_legacy_paper_config_error(raw: Dict[str, Any]):
    legacy_keys = {
        "stories",
        "font_size",
        "body_font",
        "layout",
        "page_profile",
        "style",
        "title",
        "subtitle",
        "output",
        "upload",
        "replace",
        "cleanup",
        "folder",
    }
    if "version" not in raw and legacy_keys.intersection(raw):
        raise ConfigError(
            "This looks like a legacy Goosepaper config. "
            'Paper configs now require "version": 2 and use top-level '
            '"paper", "sources", and optional "delivery" keys.'
        )


def _maybe_raise_legacy_user_config_error(raw: Dict[str, Any]):
    legacy_keys = {
        "upload",
        "replace",
        "nocase",
        "strictlysane",
        "folder",
        "cleanup",
    }
    if "version" not in raw and legacy_keys.intersection(raw):
        raise ConfigError(
            "The user config format has changed. "
            'Use a v2 file with "version": 2 and a top-level "delivery_defaults" object.'
        )


def _require_config_version(raw: Dict[str, Any], config_kind: str):
    version = raw.get("version")
    if version != CONFIG_VERSION:
        raise ConfigError(
            f"The {config_kind} must declare 'version': {CONFIG_VERSION}."
        )


def _parse_paper_settings(raw: Any) -> PaperSettings:
    section = _require_object(raw, "paper")
    _reject_unknown_keys(
        section,
        {
            "title",
            "subtitle",
            "style",
            "font_size",
            "body_font",
            "table_of_contents",
            "layout",
            "page_profile",
        },
        "paper",
    )

    title = section.get("title")
    subtitle = section.get("subtitle")
    style = section.get("style", PaperSettings.style)
    font_size = section.get("font_size", PaperSettings.font_size)
    body_font = section.get("body_font", PaperSettings.body_font)
    table_of_contents = section.get(
        "table_of_contents", PaperSettings.table_of_contents
    )
    layout = section.get("layout", PaperSettings.layout)
    page_profile = section.get("page_profile", PaperSettings.page_profile)

    return PaperSettings(
        title=title,
        subtitle=subtitle,
        style=style,
        font_size=font_size,
        body_font=body_font,
        table_of_contents=table_of_contents,
        layout=layout,
        page_profile=page_profile,
    )


def _parse_delivery_intent(raw: Any) -> DeliveryIntent:
    section = _require_object(raw, "delivery")
    _reject_unknown_keys(section, {"folder"}, "delivery")
    return DeliveryIntent(folder=section.get("folder"))


def _parse_delivery_settings(raw: Any, context: str) -> DeliverySettings:
    section = _require_object(raw, context)
    _reject_unknown_keys(section, {"folder", "replace_mode", "cleanup"}, context)

    replace_mode = section.get("replace_mode", DeliverySettings.replace_mode)
    cleanup = section.get("cleanup", DeliverySettings.cleanup)

    return DeliverySettings(
        folder=section.get("folder"),
        replace_mode=replace_mode,
        cleanup=cleanup,
    )


def _parse_sources(raw: Any) -> List[SourceConfig]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConfigError('The "sources" section must be an array.')

    sources = []
    for index, source in enumerate(raw, start=1):
        sources.append(_parse_source(source, index))
    return sources


def _parse_source(raw: Any, index: int) -> SourceConfig:
    source = _require_object(raw, f"source #{index}")
    source_type = source.get("type")
    if not isinstance(source_type, str) or not source_type:
        raise ConfigError(f'Source #{index} must include a non-empty string "type".')

    source_schema = _source_schema(source_type)
    _reject_unknown_keys(
        source,
        {"type", *source_schema["required"], *source_schema["optional"]},
        f"source #{index}",
    )

    missing = [
        key for key in source_schema["required"] if key not in source
    ]
    if missing:
        raise ConfigError(
            f"Source #{index} ({source_type}) is missing required field(s): "
            + ", ".join(missing)
            + "."
        )

    options = {key: value for key, value in source.items() if key != "type"}
    _validate_source_options(source_type, options, index)
    return SourceConfig(type=source_type, options=options)


def _source_schema(source_type: str) -> Dict[str, Any]:
    schemas = {
        "text": {
            "required": set(),
            "optional": {"headline", "text", "limit"},
        },
        "reddit": {
            "required": {"subreddit"},
            "optional": {"limit", "since_days_ago"},
        },
        "rss": {
            "required": {"url"},
            "optional": {"limit", "since_days_ago", "byline", "body_source"},
        },
        "mastodon": {
            "required": {"server", "username"},
            "optional": {"limit", "since_days_ago"},
        },
        "bluesky": {
            "required": {"username"},
            "optional": {"limit", "since_days_ago", "include_replies"},
        },
        "weather": {
            "required": {"lat", "lon"},
            "optional": {"unit", "timezone"},
        },
        "wikipedia": {
            "required": set(),
            "optional": set(),
        },
    }
    if source_type not in schemas:
        raise ConfigError(
            f'Unknown source type "{source_type}". Supported source types are: '
            + ", ".join(sorted(schemas))
            + "."
        )
    return schemas[source_type]


def _validate_source_options(source_type: str, options: Dict[str, Any], index: int):
    validators = {
        "headline": lambda value: _validate_string(value, f"source #{index} headline"),
        "text": lambda value: _validate_string(value, f"source #{index} text"),
        "limit": lambda value: _validate_positive_int(value, f"source #{index} limit"),
        "subreddit": lambda value: _validate_string(
            value, f"source #{index} subreddit"
        ),
        "url": lambda value: _validate_string(value, f"source #{index} url"),
        "server": lambda value: _validate_string(value, f"source #{index} server"),
        "username": lambda value: _validate_string(
            value, f"source #{index} username"
        ),
        "since_days_ago": lambda value: _validate_number(
            value, f"source #{index} since_days_ago"
        ),
        "byline": lambda value: _validate_rss_byline(value, index),
        "body_source": lambda value: _validate_rss_body_source(value, index),
        "include_replies": lambda value: _validate_bool(
            value, f"source #{index} include_replies"
        ),
        "lat": lambda value: _validate_number(value, f"source #{index} lat"),
        "lon": lambda value: _validate_number(value, f"source #{index} lon"),
        "timezone": lambda value: _validate_string(
            value, f"source #{index} timezone"
        ),
        "unit": lambda value: _validate_weather_unit(value, index),
    }

    for key, value in options.items():
        validators[key](value)

    if source_type == "wikipedia" and options:
        raise ConfigError("Wikipedia sources do not accept any additional fields.")


def _validate_folder(folder: Optional[str], context: str):
    if folder is None:
        return
    if not isinstance(folder, str):
        raise ValueError(f"{context} must be a string or null.")
    if folder == "":
        raise ValueError(f"{context} cannot be an empty string.")
    if "/" in folder:
        raise ValueError(f"{context} cannot contain '/'. Nested folders are not supported.")


def _validate_string(value: Any, context: str):
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{context} must be a non-empty string.")


def _validate_positive_int(value: Any, context: str):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{context} must be a positive integer.")


def _validate_number(value: Any, context: str):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{context} must be a number.")


def _validate_bool(value: Any, context: str):
    if not isinstance(value, bool):
        raise ConfigError(f"{context} must be true or false.")


def _validate_weather_unit(value: Any, index: int):
    if value not in {"F", "C"}:
        raise ConfigError(
            f'source #{index} unit must be either "F" or "C".'
        )


def _validate_rss_byline(value: Any, index: int):
    if value not in {"all", "none", "first"}:
        raise ConfigError(
            f'source #{index} byline must be one of "all", "none", or "first".'
        )


def _validate_rss_body_source(value: Any, index: int):
    if value not in {"auto", "content", "summary", "article"}:
        raise ConfigError(
            f'source #{index} body_source must be one of "auto", '
            '"content", "summary", or "article".'
        )


def _require_object(value: Any, context: str) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f'The "{context}" section must be a JSON object.')
    return value


def _reject_unknown_keys(raw: Dict[str, Any], allowed_keys: set, context: str):
    unknown = sorted(set(raw) - allowed_keys)
    if unknown:
        raise ConfigError(
            f"Unknown field(s) in {context}: " + ", ".join(unknown) + "."
        )


def _has_delivery_cli_overrides(cli_args: argparse.Namespace) -> bool:
    return any(
        [
            cli_args.folder is not None,
            cli_args.replace_mode is not None,
            cli_args.cleanup is not None,
        ]
    )
