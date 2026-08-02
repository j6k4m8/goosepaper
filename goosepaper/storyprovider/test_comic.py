import base64
import datetime

import pytest

from . import comic

_XKCD_HTML = b"""
<html><body>
<div id="comic">
<img src="//imgs.xkcd.com/comics/todays_strip.png" title="hover joke text" alt="Todays Strip"/>
</div>
</body></html>
"""

_CAH_HTML = b"""
<html><body>
<img class="Comic_comic__image__abc123 Comic_comic__abc" src="https://assets.gocomics.com/strip.gif" />
</body></html>
"""

_GARFIELD_HTML = b"""
<html><body>
<img id="comic-zoom" src="/img/garfield-today.jpg" />
</body></html>
"""

_FAKE_IMAGE_BYTES = b"\x89PNGfakebytes"


class _FakeResponse:
    def __init__(self, content: bytes, headers: dict = None):
        self.content = content
        self.headers = headers or {}

    def raise_for_status(self):
        return None


def test_unknown_comic_type_is_rejected():
    with pytest.raises(ValueError):
        comic.DailyComicStoryProvider(comic_type="dilbert")


def test_xkcd_fetches_title_and_hover_text_and_embeds_image(monkeypatch):
    calls = []

    def fake_get(url, *, headers, timeout):
        calls.append(url)
        if url == "https://xkcd.com":
            return _FakeResponse(_XKCD_HTML)
        assert url == "https://imgs.xkcd.com/comics/todays_strip.png"
        return _FakeResponse(_FAKE_IMAGE_BYTES, headers={"Content-Type": "image/png"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="xkcd")
    stories = provider.get_stories()

    assert len(stories) == 1
    story = stories[0]
    assert story.headline == "Todays Strip"
    assert story.byline == "XKCD"
    assert "hover joke text" in story.body_html
    encoded = base64.b64encode(_FAKE_IMAGE_BYTES).decode("ascii")
    assert f"data:image/png;base64,{encoded}" in story.body_html
    assert calls == [
        "https://xkcd.com",
        "https://imgs.xkcd.com/comics/todays_strip.png",
    ]


def test_calvin_and_hobbes_uses_date_scoped_url_and_browser_headers(monkeypatch):
    seen = {"urls": [], "headers": []}

    def fake_get(url, *, headers, timeout):
        seen["urls"].append(url)
        seen["headers"].append(headers)
        if "gocomics.com" in url:
            return _FakeResponse(_CAH_HTML)
        assert url == "https://assets.gocomics.com/strip.gif"
        return _FakeResponse(_FAKE_IMAGE_BYTES, headers={"Content-Type": "image/gif"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="cah", date=datetime.date(2026, 1, 5)
    )
    stories = provider.get_stories()

    assert seen["urls"][0] == "https://www.gocomics.com/calvinandhobbes/2026/01/05"
    # Both the page request and the follow-up image request need gocomics.com's
    # browser-like headers - see the "cah" entry in _COMIC_SOURCES.
    for headers in seen["headers"]:
        assert headers["User-Agent"].startswith("Mozilla/5.0")
        assert headers["Accept-Language"] == "en"

    story = stories[0]
    assert story.headline == "Calvin and Hobbes – January 05, 2026"
    assert story.byline == "Calvin and Hobbes"
    assert story.date == datetime.datetime(2026, 1, 5)


def test_garfield_has_no_title_or_custom_headers(monkeypatch):
    seen_headers = []

    def fake_get(url, *, headers, timeout):
        seen_headers.append(headers)
        if "arcamax.com" in url:
            return _FakeResponse(_GARFIELD_HTML)
        assert url == "https://www.arcamax.com/img/garfield-today.jpg"
        return _FakeResponse(_FAKE_IMAGE_BYTES, headers={"Content-Type": "image/jpeg"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="garfield")
    stories = provider.get_stories()

    assert seen_headers == [{}, {}]
    assert stories[0].byline == "Garfield"
    assert stories[0].headline.startswith("Garfield – ")


def test_missing_strip_image_raises_informative_error(monkeypatch):
    def fake_get(url, *, headers, timeout):
        return _FakeResponse(b"<html><body>no comic here</body></html>")

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="xkcd")
    with pytest.raises(RuntimeError, match="Could not find today's XKCD strip"):
        provider.get_stories()
