import json
import os
import tempfile
from pathlib import Path

from .config import (
    ConfigError,
    DeliveryIntent,
    DeliverySettings,
    load_paper_config,
    load_user_config,
    resolve_delivery_settings,
    resolve_runtime_config,
)


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class _TempWorkspace:
    def __enter__(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self._old_cwd = Path.cwd()
        self._old_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.chdir(self.root)
        return self.root

    def __exit__(self, exc_type, exc, tb):
        os.chdir(self._old_cwd)
        if self._old_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self._old_xdg
        self._tmpdir.cleanup()


def _assert_config_error(fn, message_fragment: str):
    try:
        fn()
    except ConfigError as err:
        assert message_fragment in str(err)
    else:
        assert False, "Expected ConfigError"


def test_load_paper_config_uses_v2_schema():
    with _TempWorkspace() as tmp_path:
        config_path = tmp_path / "paper.json"
        _write_json(
            config_path,
            {
                "version": 2,
                "paper": {
                    "title": "Daily Goosepaper",
                    "style": "Autumn",
                    "font_size": 16,
                    "body_font": "Literata",
                    "table_of_contents": True,
                    "layout": "1col",
                    "page_profile": "letter",
                },
                "sources": [
                    {
                        "type": "rss",
                        "url": "https://example.com/feed.xml",
                        "limit": 3,
                        "byline": "first",
                        "body_source": "summary",
                    },
                    {
                        "type": "bluesky",
                        "username": "jordan.matelsky.com",
                        "limit": 2,
                    }
                ],
                "delivery": {"folder": "Morning Brief"},
            },
        )

        config = load_paper_config(config_path)

        assert config.paper.title == "Daily Goosepaper"
        assert config.paper.style == "Autumn"
        assert config.paper.font_size == 16
        assert config.paper.body_font == "Literata"
        assert config.paper.table_of_contents is True
        assert config.paper.layout == "1col"
        assert config.paper.page_profile == "letter"
        assert config.sources[0].type == "rss"
        assert config.sources[0].options["url"] == "https://example.com/feed.xml"
        assert config.sources[0].options["byline"] == "first"
        assert config.sources[0].options["body_source"] == "summary"
        assert config.sources[1].type == "bluesky"
        assert config.sources[1].options["username"] == "jordan.matelsky.com"
        assert config.delivery.folder == "Morning Brief"


def test_load_user_config_defaults_when_missing():
    with _TempWorkspace() as tmp_path:
        os.environ["XDG_CONFIG_HOME"] = str(tmp_path)

        config = load_user_config()

        assert config.delivery_defaults == DeliverySettings()


def test_resolve_delivery_settings_paper_folder_overrides_user_default():
    delivery = resolve_delivery_settings(
        user_defaults=DeliverySettings(
            folder="Default Folder",
            replace_mode="nocase",
            cleanup=False,
        ),
        folder_override=None,
        paper_delivery=None,
    )
    assert delivery.folder == "Default Folder"

    delivery = resolve_delivery_settings(
        user_defaults=DeliverySettings(
            folder="Default Folder",
            replace_mode="nocase",
            cleanup=False,
        ),
        paper_delivery=DeliveryIntent(folder="Morning Brief"),
    )
    assert delivery.folder == "Morning Brief"


def test_resolve_runtime_config_merges_user_defaults_and_cli():
    with _TempWorkspace() as tmp_path:
        os.environ["XDG_CONFIG_HOME"] = str(tmp_path / "xdg")

        _write_json(
            tmp_path / "goosepaper.json",
            {
                "version": 2,
                "paper": {"style": "Academy"},
                "sources": [{"type": "text", "headline": "hello"}],
                "delivery": {"folder": "Morning Brief"},
            },
        )
        _write_json(
            tmp_path / "xdg" / "goosepaper" / "config.json",
            {
                "version": 2,
                "delivery_defaults": {
                    "replace_mode": "nocase",
                    "cleanup": True,
                    "folder": "Default Folder",
                },
            },
        )

        config = resolve_runtime_config(
            ["--deliver", "--replace-mode", "exact", "--no-cleanup"]
        )

        assert config.paper.style == "Academy"
        assert config.delivery.folder == "Morning Brief"
        assert config.delivery.replace_mode == "exact"
        assert config.delivery.cleanup is False
        assert config.deliver is True


def test_load_paper_config_accepts_auto_layout_and_null_body_font():
    with _TempWorkspace() as tmp_path:
        config_path = tmp_path / "paper.json"
        _write_json(
            config_path,
            {
                "version": 2,
                "paper": {
                    "style": "FifthAvenue",
                    "layout": "auto",
                    "body_font": None,
                    "table_of_contents": False,
                    "page_profile": "remarkable2",
                },
                "sources": [],
            },
        )

        config = load_paper_config(config_path)

        assert config.paper.layout == "auto"
        assert config.paper.body_font is None
        assert config.paper.table_of_contents is False
        assert config.paper.page_profile == "remarkable2"


def test_load_paper_config_accepts_rm1_page_profile_alias():
    with _TempWorkspace() as tmp_path:
        config_path = tmp_path / "paper.json"
        _write_json(
            config_path,
            {
                "version": 2,
                "paper": {
                    "style": "FifthAvenue",
                    "page_profile": "rm1",
                },
                "sources": [],
            },
        )

        config = load_paper_config(config_path)

        assert config.paper.page_profile == "rm1"


def test_resolve_runtime_config_rejects_legacy_config():
    with _TempWorkspace() as tmp_path:
        _write_json(
            tmp_path / "goosepaper.json",
            {
                "font_size": 14,
                "stories": [],
            },
        )

        _assert_config_error(
            lambda: resolve_runtime_config([]),
            "legacy Goosepaper config",
        )


def test_resolve_runtime_config_requires_output_for_nostory():
    _assert_config_error(
        lambda: resolve_runtime_config(["--deliver", "--nostory"]),
        "--output",
    )


def test_load_paper_config_rejects_invalid_rss_byline_mode():
    with _TempWorkspace() as tmp_path:
        config_path = tmp_path / "paper.json"
        _write_json(
            config_path,
            {
                "version": 2,
                "paper": {"style": "FifthAvenue"},
                "sources": [
                    {
                        "type": "rss",
                        "url": "https://example.com/feed.xml",
                        "byline": "sometimes",
                    }
                ],
            },
        )

        _assert_config_error(
            lambda: load_paper_config(config_path),
            'byline must be one of "all", "none", or "first"',
        )


def test_load_paper_config_rejects_invalid_rss_body_source():
    with _TempWorkspace() as tmp_path:
        config_path = tmp_path / "paper.json"
        _write_json(
            config_path,
            {
                "version": 2,
                "paper": {"style": "FifthAvenue"},
                "sources": [
                    {
                        "type": "rss",
                        "url": "https://example.com/feed.xml",
                        "body_source": "feed",
                    }
                ],
            },
        )

        _assert_config_error(
            lambda: load_paper_config(config_path),
            'body_source must be one of "auto", "content", '
            '"summary", or "article"',
        )


def test_load_paper_config_accepts_bluesky_source():
    with _TempWorkspace() as tmp_path:
        config_path = tmp_path / "paper.json"
        _write_json(
            config_path,
            {
                "version": 2,
                "paper": {"style": "FifthAvenue"},
                "sources": [
                    {
                        "type": "bluesky",
                        "username": "infinitescream.bsky.social",
                    }
                ],
            },
        )

        config = load_paper_config(config_path)

        assert config.sources[0].type == "bluesky"
        assert config.sources[0].options["username"] == "infinitescream.bsky.social"
