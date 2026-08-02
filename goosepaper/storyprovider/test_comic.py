import base64
import datetime
import io

import pytest
from PIL import Image

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


def _image_bytes(fmt: str, mode: str = "RGB", size=(4, 3), color=(200, 50, 10)) -> bytes:
    image = Image.new(mode, size, color if mode != "L" else 128)
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def _decode_data_uri_image(body_html: str) -> Image.Image:
    prefix = "data:image/jpeg;base64,"
    start = body_html.index(prefix) + len(prefix)
    end = body_html.index('"', start)
    payload = base64.b64decode(body_html[start:end])
    return Image.open(io.BytesIO(payload))


class _FakeResponse:
    def __init__(self, content: bytes, headers: dict = None):
        self.content = content
        self.headers = headers or {}

    def raise_for_status(self):
        return None


def test_unknown_comic_type_is_rejected():
    with pytest.raises(ValueError):
        comic.DailyComicStoryProvider(comic_type="dilbert")


def test_xkcd_uses_fixed_headline_and_no_byline_but_keeps_hover_text(monkeypatch):
    """XKCD's own per-day title (the <img> alt text, "Todays Strip" in the fixture) is
    deliberately NOT used as the headline - see get_stories()'s docstring on why a fixed,
    source-derived headline (and no byline) is used for every comic instead."""
    calls = []
    fake_png = _image_bytes("PNG", size=(5, 4))

    def fake_get(url, *, headers, timeout):
        calls.append(url)
        if url == "https://xkcd.com":
            return _FakeResponse(_XKCD_HTML)
        assert url == "https://imgs.xkcd.com/comics/todays_strip.png"
        return _FakeResponse(fake_png, headers={"Content-Type": "image/png"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="xkcd")
    stories = provider.get_stories()

    assert len(stories) == 1
    story = stories[0]
    assert story.headline == "XKCD"
    assert story.byline is None
    assert "hover joke text" in story.body_html
    embedded = _decode_data_uri_image(story.body_html)
    assert embedded.size == (5, 4)
    assert calls == [
        "https://xkcd.com",
        "https://imgs.xkcd.com/comics/todays_strip.png",
    ]


def test_calvin_and_hobbes_uses_date_scoped_url_and_browser_headers(monkeypatch):
    seen = {"urls": [], "headers": []}
    fake_gif = _image_bytes("GIF", size=(6, 5))

    def fake_get(url, *, headers, timeout):
        seen["urls"].append(url)
        seen["headers"].append(headers)
        # Both the page (www.gocomics.com) and image (assets.gocomics.com) URLs contain
        # "gocomics.com" - route on the exact page URL instead of a substring check.
        if url == "https://www.gocomics.com/calvinandhobbes/2026/01/05":
            return _FakeResponse(_CAH_HTML)
        assert url == "https://assets.gocomics.com/strip.gif"
        return _FakeResponse(fake_gif, headers={"Content-Type": "image/gif"})

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
    assert story.headline == "Calvin and Hobbes"
    assert story.byline is None
    assert story.date == datetime.datetime(2026, 1, 5)
    embedded = _decode_data_uri_image(story.body_html)
    assert embedded.size == (6, 5)


def test_garfield_has_no_title_or_custom_headers(monkeypatch):
    seen_headers = []
    fake_jpeg = _image_bytes("JPEG", size=(7, 6))

    def fake_get(url, *, headers, timeout):
        seen_headers.append(headers)
        # Both the page and image URLs live on www.arcamax.com - route on the exact page URL
        # instead of a substring check.
        if url == "https://www.arcamax.com/thefunnies/garfield/":
            return _FakeResponse(_GARFIELD_HTML)
        assert url == "https://www.arcamax.com/img/garfield-today.jpg"
        return _FakeResponse(fake_jpeg, headers={"Content-Type": "image/jpeg"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="garfield")
    stories = provider.get_stories()

    assert seen_headers == [{}, {}]
    assert stories[0].byline is None
    assert stories[0].headline == "Garfield"
    embedded = _decode_data_uri_image(stories[0].body_html)
    assert embedded.size == (7, 6)


def test_cmyk_jpeg_is_converted_to_rgb_jpeg(monkeypatch):
    """Regression test: arcamax.com serves Garfield as a CMYK JPEG with a large embedded
    Photoshop/ICC metadata block. Passing those bytes through to WeasyPrint unmodified made it
    silently drop the *entire* story - no exception, no image, no text, nothing in the rendered
    PDF - while every other story in the same document rendered fine. Decoding and re-encoding
    through Pillow (see get_stories()'s docstring) must always produce a plain RGB/L JPEG,
    regardless of the source image's color mode."""
    fake_cmyk_jpeg = _image_bytes("JPEG", mode="CMYK", size=(8, 8))

    def fake_get(url, *, headers, timeout):
        if url == "https://www.arcamax.com/thefunnies/garfield/":
            return _FakeResponse(_GARFIELD_HTML)
        return _FakeResponse(fake_cmyk_jpeg, headers={"Content-Type": "image/jpeg"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="garfield")
    stories = provider.get_stories()

    assert "data:image/jpeg;base64," in stories[0].body_html
    embedded = _decode_data_uri_image(stories[0].body_html)
    assert embedded.format == "JPEG"
    assert embedded.mode in ("RGB", "L")


def test_oversized_source_image_is_downscaled(monkeypatch):
    """Regression test: gocomics.com's CDN can serve a strip at print resolution (observed:
    2800px wide) with no smaller variant requested. Combined with the hundreds of other images
    already in a full newspaper, the resulting near-1MB base64 payload for a single story was
    reproduced to make WeasyPrint silently drop that story's entire content. Every embedded
    comic must be capped to comic._MAX_IMAGE_DIMENSION on its long edge, regardless of source
    resolution."""
    oversized = _image_bytes("PNG", size=(2800, 2000))

    def fake_get(url, *, headers, timeout):
        if url == "https://xkcd.com":
            return _FakeResponse(_XKCD_HTML)
        return _FakeResponse(oversized, headers={"Content-Type": "image/png"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="xkcd")
    stories = provider.get_stories()

    embedded = _decode_data_uri_image(stories[0].body_html)
    assert max(embedded.size) == comic._MAX_IMAGE_DIMENSION
    # Aspect ratio preserved: 2800x2000 is 1.4:1, so the capped long edge (width) implies a
    # short edge (height) of 1200 / 1.4.
    assert embedded.size == (1200, int(2000 * 1200 / 2800))


def test_missing_strip_image_raises_informative_error(monkeypatch):
    def fake_get(url, *, headers, timeout):
        return _FakeResponse(b"<html><body>no comic here</body></html>")

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="xkcd")
    with pytest.raises(RuntimeError, match="Could not find today's XKCD strip"):
        provider.get_stories()
