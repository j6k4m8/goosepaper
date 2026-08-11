import base64
import datetime
import io
import json

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


def _gocomics_html(series_name: str = "Calvin and Hobbes") -> bytes:
    ld_json = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "ComicStory",
            "name": f"{series_name} - January 5, 2026",
            "datePublished": "2026-01-05",
            "isPartOf": {
                "@type": "ComicSeries",
                "name": series_name,
                "url": "https://www.gocomics.com/calvinandhobbes",
            },
        }
    )
    return f"""
    <html><body>
    <script type="application/ld+json">{ld_json}</script>
    <img class="Comic_comic__image__abc123 Comic_comic__abc" src="https://assets.gocomics.com/strip.gif" />
    </body></html>
    """.encode()


def _arcamax_html(series_name: str = "Garfield") -> bytes:
    return f"""
    <html><head>
    <meta property="og:title" content="{series_name}" />
    </head><body>
    <img id="comic-zoom" src="/img/today.jpg" />
    </body></html>
    """.encode()


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


def test_gocomics_without_comic_name_is_rejected():
    with pytest.raises(ValueError, match="requires a comic_name"):
        comic.DailyComicStoryProvider(comic_type="gocomics")


def test_arcamax_without_comic_name_is_rejected():
    with pytest.raises(ValueError, match="requires a comic_name"):
        comic.DailyComicStoryProvider(comic_type="arcamax")


def test_xkcd_with_comic_name_is_rejected():
    with pytest.raises(ValueError, match="does not take a comic_name"):
        comic.DailyComicStoryProvider(comic_type="xkcd", comic_name="xkcd")


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


def test_gocomics_uses_date_scoped_url_browser_headers_and_derives_label(monkeypatch):
    seen = {"urls": [], "headers": []}
    fake_gif = _image_bytes("GIF", size=(6, 5))

    def fake_get(url, *, headers, timeout):
        seen["urls"].append(url)
        seen["headers"].append(headers)
        if url == "https://www.gocomics.com/calvinandhobbes/2026/01/05":
            return _FakeResponse(_gocomics_html("Calvin and Hobbes"))
        assert url == "https://assets.gocomics.com/strip.gif"
        return _FakeResponse(fake_gif, headers={"Content-Type": "image/gif"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="gocomics", comic_name="calvinandhobbes", date=datetime.date(2026, 1, 5)
    )
    stories = provider.get_stories()

    assert seen["urls"][0] == "https://www.gocomics.com/calvinandhobbes/2026/01/05"
    # Both the page request and the follow-up image request need gocomics.com's
    # browser-like headers - see the "gocomics" entry in _COMIC_SOURCES.
    for headers in seen["headers"]:
        assert headers["User-Agent"].startswith("Mozilla/5.0")
        assert headers["Accept-Language"] == "en"

    story = stories[0]
    # Label is derived from the page's JSON-LD, not hardcoded per comic.
    assert story.headline == "Calvin and Hobbes"
    assert story.byline is None
    assert story.date == datetime.datetime(2026, 1, 5)
    embedded = _decode_data_uri_image(story.body_html)
    assert embedded.size == (6, 5)


def test_gocomics_derives_label_for_a_different_comic_without_any_code_change(monkeypatch):
    """The whole point of the generic gocomics/arcamax sources: any comic on that site works
    purely by passing a different comic_name, with no new _ComicSource entry or label mapping."""
    fake_gif = _image_bytes("GIF", size=(3, 3))

    def fake_get(url, *, headers, timeout):
        if url == "https://www.gocomics.com/pearlsbeforeswine/2026/01/05":
            return _FakeResponse(_gocomics_html("Pearls Before Swine"))
        return _FakeResponse(fake_gif, headers={"Content-Type": "image/gif"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="gocomics", comic_name="pearlsbeforeswine", date=datetime.date(2026, 1, 5)
    )
    stories = provider.get_stories()

    assert stories[0].headline == "Pearls Before Swine"


def test_gocomics_missing_label_raises_even_though_image_was_found(monkeypatch):
    """A page with the strip <img> but no (or malformed) JSON-LD indicates the site's template
    changed - fail loudly instead of embedding a comic with no headline."""
    fake_gif = _image_bytes("GIF", size=(3, 3))

    def fake_get(url, *, headers, timeout):
        if url == "https://www.gocomics.com/calvinandhobbes/2026/01/05":
            return _FakeResponse(
                b'<html><body><img class="comic image" src="https://a/strip.gif" /></body></html>'
            )
        return _FakeResponse(fake_gif, headers={"Content-Type": "image/gif"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="gocomics", comic_name="calvinandhobbes", date=datetime.date(2026, 1, 5)
    )
    with pytest.raises(RuntimeError, match="Could not determine the comic's display name"):
        provider.get_stories()


def test_arcamax_derives_label_from_og_title_and_has_no_custom_headers(monkeypatch):
    seen_headers = []
    fake_jpeg = _image_bytes("JPEG", size=(7, 6))

    def fake_get(url, *, headers, timeout):
        seen_headers.append(headers)
        if url == "https://www.arcamax.com/thefunnies/garfield/":
            return _FakeResponse(_arcamax_html("Garfield"))
        assert url == "https://www.arcamax.com/img/today.jpg"
        return _FakeResponse(fake_jpeg, headers={"Content-Type": "image/jpeg"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="arcamax", comic_name="garfield")
    stories = provider.get_stories()

    assert seen_headers == [{}, {}]
    assert stories[0].byline is None
    assert stories[0].headline == "Garfield"
    embedded = _decode_data_uri_image(stories[0].body_html)
    assert embedded.size == (7, 6)


def test_arcamax_derives_label_for_a_different_comic_without_any_code_change(monkeypatch):
    fake_jpeg = _image_bytes("JPEG", size=(3, 3))

    def fake_get(url, *, headers, timeout):
        if url == "https://www.arcamax.com/thefunnies/beetlebailey/":
            return _FakeResponse(_arcamax_html("Beetle Bailey"))
        return _FakeResponse(fake_jpeg, headers={"Content-Type": "image/jpeg"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="arcamax", comic_name="beetlebailey")
    stories = provider.get_stories()

    assert stories[0].headline == "Beetle Bailey"


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
            return _FakeResponse(_arcamax_html("Garfield"))
        return _FakeResponse(fake_cmyk_jpeg, headers={"Content-Type": "image/jpeg"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="arcamax", comic_name="garfield")
    stories = provider.get_stories()

    assert "data:image/jpeg;base64," in stories[0].body_html
    embedded = _decode_data_uri_image(stories[0].body_html)
    assert embedded.format == "JPEG"
    assert embedded.mode in ("RGB", "L")


def test_transparent_source_image_is_composited_onto_white(monkeypatch):
    """Regression test: Pillow's convert("RGB") does not composite transparent pixels against
    anything - it just drops the alpha channel and keeps whatever RGB value was stored
    underneath, which can leave visible phantom colors where transparency was meant to show
    through (verified directly against Pillow: a semi-transparent black RGBA pixel converts to
    solid black, not white, and a GIF-style transparency-color-keyed pixel converts to its own
    (arbitrarily-colored) palette entry, not white). A comic strip with any transparency must be
    composited onto white before the alpha channel is dropped - the newspaper page underneath is
    always white in every bundled goosepaper style."""
    fake_png = io.BytesIO()
    rgba = Image.new("RGBA", (2, 2), (255, 255, 255, 0))  # fully transparent white
    rgba.putpixel((0, 0), (0, 0, 0, 255))  # opaque black - must stay black
    rgba.putpixel((1, 1), (10, 20, 30, 0))  # fully transparent, garbage RGB - must become white
    rgba.save(fake_png, format="PNG")
    fake_png_bytes = fake_png.getvalue()

    def fake_get(url, *, headers, timeout):
        if url == "https://xkcd.com":
            return _FakeResponse(_XKCD_HTML)
        return _FakeResponse(fake_png_bytes, headers={"Content-Type": "image/png"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="xkcd")
    stories = provider.get_stories()

    embedded = _decode_data_uri_image(stories[0].body_html)
    assert embedded.mode == "RGB"
    assert embedded.getpixel((0, 0)) == (0, 0, 0)
    assert embedded.getpixel((1, 1)) == (255, 255, 255)


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
    with pytest.raises(RuntimeError, match="Could not find today's strip"):
        provider.get_stories()


def test_gocomics_falls_back_to_previous_day_when_todays_strip_is_missing(monkeypatch, capsys):
    """Regression test: gocomics.com's daily rollover time/timezone isn't documented, so
    generation running earlier in the day than that (unknown) rollover would otherwise fail
    every single time - see comic.py's _MAX_FALLBACK_DAYS docstring. Falling back a day must
    (a) still return the previous day's strip rather than raising, (b) leave no trace of the
    fallback in the Story itself (headline/date/body - the reader shouldn't see a difference),
    and (c) only be surfaced as a log line, per the addon maintainer's explicit call."""
    seen_urls = []
    fake_gif = _image_bytes("GIF", size=(6, 5))

    def fake_get(url, *, headers, timeout):
        seen_urls.append(url)
        if url == "https://www.gocomics.com/calvinandhobbes/2026/01/05":
            return _FakeResponse(b"<html><body>not published yet</body></html>")
        if url == "https://www.gocomics.com/calvinandhobbes/2026/01/04":
            return _FakeResponse(_gocomics_html("Calvin and Hobbes"))
        assert url == "https://assets.gocomics.com/strip.gif"
        return _FakeResponse(fake_gif, headers={"Content-Type": "image/gif"})

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="gocomics", comic_name="calvinandhobbes", date=datetime.date(2026, 1, 5)
    )
    stories = provider.get_stories()

    assert seen_urls == [
        "https://www.gocomics.com/calvinandhobbes/2026/01/05",
        "https://www.gocomics.com/calvinandhobbes/2026/01/04",
        "https://assets.gocomics.com/strip.gif",
    ]
    story = stories[0]
    # No visible trace of the fallback - same headline/date/body shape as the normal case.
    assert story.headline == "Calvin and Hobbes"
    assert story.date == datetime.datetime(2026, 1, 5)
    assert '<p class="comic-subtitle">' not in story.body_html
    embedded = _decode_data_uri_image(story.body_html)
    assert embedded.size == (6, 5)

    log_output = capsys.readouterr().out
    assert "2026-01-05" in log_output
    assert "2026-01-04" in log_output


def test_gocomics_gives_up_after_max_fallback_days_and_reports_originally_requested_url(
    monkeypatch,
):
    def fake_get(url, *, headers, timeout):
        return _FakeResponse(b"<html><body>never published</body></html>")

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="gocomics", comic_name="calvinandhobbes", date=datetime.date(2026, 1, 5)
    )
    with pytest.raises(
        RuntimeError,
        match=r"Could not find today's strip at "
        r"https://www\.gocomics\.com/calvinandhobbes/2026/01/05",
    ):
        provider.get_stories()


def test_xkcd_does_not_retry_across_dates_since_its_url_is_not_date_scoped(monkeypatch):
    """xkcd's page_url has no {date} placeholder, so a miss must raise immediately instead of
    re-fetching the same URL comic._MAX_FALLBACK_DAYS+1 times for no benefit."""
    calls = []

    def fake_get(url, *, headers, timeout):
        calls.append(url)
        return _FakeResponse(b"<html><body>no comic here</body></html>")

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="xkcd")
    with pytest.raises(RuntimeError):
        provider.get_stories()

    assert calls == ["https://xkcd.com"]


def test_arcamax_does_not_retry_across_dates_since_its_url_is_not_date_scoped(monkeypatch):
    calls = []

    def fake_get(url, *, headers, timeout):
        calls.append(url)
        return _FakeResponse(b"<html><body>no comic here</body></html>")

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="arcamax", comic_name="garfield")
    with pytest.raises(RuntimeError):
        provider.get_stories()

    assert calls == ["https://www.arcamax.com/thefunnies/garfield/"]
