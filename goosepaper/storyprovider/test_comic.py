import datetime
import json

import pytest

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

    def fake_get(url, *, headers, timeout):
        calls.append(url)
        return _FakeResponse(_XKCD_HTML)

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="xkcd")
    stories = provider.get_stories()

    assert len(stories) == 1
    story = stories[0]
    assert story.headline == "XKCD"
    assert story.byline is None
    assert "hover joke text" in story.body_html
    assert 'src="https://imgs.xkcd.com/comics/todays_strip.png"' in story.body_html
    # Only the page is fetched - the strip image is left as a remote link for the render step
    # to fetch/embed later (see get_stories()'s docstring).
    assert calls == ["https://xkcd.com"]


def test_gocomics_uses_date_scoped_url_and_browser_headers_and_derives_label(monkeypatch):
    seen = {"urls": [], "headers": []}

    def fake_get(url, *, headers, timeout):
        seen["urls"].append(url)
        seen["headers"].append(headers)
        return _FakeResponse(_gocomics_html("Calvin and Hobbes"))

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="gocomics", comic_name="calvinandhobbes", date=datetime.date(2026, 1, 5)
    )
    stories = provider.get_stories()

    assert seen["urls"] == ["https://www.gocomics.com/calvinandhobbes/2026/01/05"]
    # Only the page fetch needs gocomics.com's browser-like headers - see the "gocomics" entry
    # in _COMIC_SOURCES and get_stories()'s docstring (the strip image itself, on gocomics.com's
    # own CDN, isn't header-gated).
    assert seen["headers"][0]["User-Agent"].startswith("Mozilla/5.0")
    assert seen["headers"][0]["Accept-Language"] == "en"

    story = stories[0]
    # Label is derived from the page's JSON-LD, not hardcoded per comic.
    assert story.headline == "Calvin and Hobbes"
    assert story.byline is None
    assert story.date == datetime.datetime(2026, 1, 5)
    assert 'src="https://assets.gocomics.com/strip.gif"' in story.body_html


def test_gocomics_derives_label_for_a_different_comic_without_any_code_change(monkeypatch):
    """The whole point of the generic gocomics/arcamax sources: any comic on that site works
    purely by passing a different comic_name, with no new _ComicSource entry or label mapping."""

    def fake_get(url, *, headers, timeout):
        return _FakeResponse(_gocomics_html("Pearls Before Swine"))

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="gocomics", comic_name="pearlsbeforeswine", date=datetime.date(2026, 1, 5)
    )
    stories = provider.get_stories()

    assert stories[0].headline == "Pearls Before Swine"


def test_gocomics_missing_label_raises_even_though_image_was_found(monkeypatch):
    """A page with the strip <img> but no (or malformed) JSON-LD indicates the site's template
    changed - fail loudly instead of embedding a comic with no headline."""

    def fake_get(url, *, headers, timeout):
        return _FakeResponse(
            b'<html><body><img class="comic image" src="https://a/strip.gif" /></body></html>'
        )

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="gocomics", comic_name="calvinandhobbes", date=datetime.date(2026, 1, 5)
    )
    with pytest.raises(RuntimeError, match="Could not determine the comic's display name"):
        provider.get_stories()


def test_arcamax_derives_label_from_og_title_and_has_no_custom_headers(monkeypatch):
    seen_headers = []

    def fake_get(url, *, headers, timeout):
        seen_headers.append(headers)
        return _FakeResponse(_arcamax_html("Garfield"))

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="arcamax", comic_name="garfield")
    stories = provider.get_stories()

    assert seen_headers == [{}]
    assert stories[0].byline is None
    assert stories[0].headline == "Garfield"
    assert 'src="https://www.arcamax.com/img/today.jpg"' in stories[0].body_html


def test_arcamax_derives_label_for_a_different_comic_without_any_code_change(monkeypatch):
    def fake_get(url, *, headers, timeout):
        return _FakeResponse(_arcamax_html("Beetle Bailey"))

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="arcamax", comic_name="beetlebailey")
    stories = provider.get_stories()

    assert stories[0].headline == "Beetle Bailey"


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

    def fake_get(url, *, headers, timeout):
        seen_urls.append(url)
        if url == "https://www.gocomics.com/calvinandhobbes/2026/01/05":
            return _FakeResponse(b"<html><body>not published yet</body></html>")
        assert url == "https://www.gocomics.com/calvinandhobbes/2026/01/04"
        return _FakeResponse(_gocomics_html("Calvin and Hobbes"))

    monkeypatch.setattr(comic.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(
        comic_type="gocomics", comic_name="calvinandhobbes", date=datetime.date(2026, 1, 5)
    )
    stories = provider.get_stories()

    assert seen_urls == [
        "https://www.gocomics.com/calvinandhobbes/2026/01/05",
        "https://www.gocomics.com/calvinandhobbes/2026/01/04",
    ]
    story = stories[0]
    # No visible trace of the fallback - same headline/date/body shape as the normal case.
    assert story.headline == "Calvin and Hobbes"
    assert story.date == datetime.datetime(2026, 1, 5)
    assert '<p class="comic-subtitle">' not in story.body_html
    assert 'src="https://assets.gocomics.com/strip.gif"' in story.body_html

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
