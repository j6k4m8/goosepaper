"""Daily comic strip embedding - XKCD, Calvin and Hobbes, and Garfield.

The fetch mechanism for each comic (page URL, per-comic HTTP headers, and the XPath used to
find the strip's <img> tag) is ported directly from evidlo/remarkable_news's per-comic systemd
service files (services/xkcd.service, services/cah.service, services/garfield.service) - see
https://github.com/evidlo/remarkable_news. That project renders comics onto a reMarkable's
suspend screen via a small Go CLI (`renews`) driven entirely by CLI flags (-url/-xpath/-header/
-strftime); this module reimplements the same three lookups natively in Python for Goosepaper,
downloading the strip once as a Story rather than as a device-side background poller.
"""

from __future__ import annotations

import base64
import datetime
import io
from dataclasses import dataclass, field
from html import escape
from typing import Dict, List, Optional

import requests
from lxml import html as lxml_html
from PIL import Image

from ..story import Story
from .storyprovider import StoryProvider

_DEFAULT_TIMEOUT = 20

# Some sources (gocomics.com's CDN in particular) serve a source-agnostic "print" resolution
# far beyond anything a newspaper page needs (observed: 2800px wide). At that size, the
# resulting base64 data: URI approaches multi-MB territory; embedded alongside the hundreds
# of other images in a full newspaper, that was enough to make WeasyPrint silently drop the
# story's entire content with no error. Capping the long edge here keeps every comic embed in
# the same reasonable size range as a typical article thumbnail, regardless of what resolution
# the source happens to serve today.
_MAX_IMAGE_DIMENSION = 1200

_COMIC_CSS = """
<style>
.comic-strip-body { text-align: center; }
.comic-strip-body img.comic-strip { max-width: 100%; height: auto; }
.comic-subtitle { font-size: 0.85em; font-style: italic; color: #444; margin-top: 0.4em; }
</style>
"""


@dataclass(frozen=True)
class _ComicSource:
    label: str
    # May contain a {date} strftime-style placeholder for per-day URLs (see "cah" below).
    page_url: str
    image_xpath: str
    subtitle_xpath: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


# Ported from evidlo/remarkable_news's services/*.service files - see module docstring.
_COMIC_SOURCES: Dict[str, _ComicSource] = {
    "xkcd": _ComicSource(
        label="XKCD",
        page_url="https://xkcd.com",
        image_xpath='//div[@id="comic"]/img/@src',
        # The title attribute is the famous mouseover joke, shown as a caption under the strip.
        # (The strip's own dynamic title, in the alt attribute, is deliberately not used - see
        # the "headline" note in get_stories()'s docstring.)
        subtitle_xpath='//div[@id="comic"]/img/@title',
    ),
    "cah": _ComicSource(
        label="Calvin and Hobbes",
        page_url="https://www.gocomics.com/calvinandhobbes/{date:%Y}/{date:%m}/{date:%d}",
        image_xpath="//img[contains(@class, 'comic') and contains(@class, 'image')]/@src",
        # gocomics.com blocks non-browser-looking requests without these.
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0"
            ),
            "Accept-Language": "en",
            "Accept": "*/*",
        },
    ),
    "garfield": _ComicSource(
        label="Garfield",
        page_url="https://www.arcamax.com/thefunnies/garfield/",
        image_xpath='//img[@id="comic-zoom"]/@src',
    ),
}


def _first(values: List[str]) -> Optional[str]:
    return values[0] if values else None


class DailyComicStoryProvider(StoryProvider):
    """Downloads today's strip of a daily comic and embeds it as a single image Story.

    Constructor parameters:
      - `comic_type` (required): one of `"xkcd"`, `"cah"` (Calvin and Hobbes), `"garfield"`.
        No default - a config that forgets it should fail loudly instead of silently always
        fetching XKCD.
      - `date` (optional, default today): which day's strip to fetch. Only meaningful for
        `"cah"`, whose page URL is date-scoped (`gocomics.com/calvinandhobbes/YYYY/MM/DD`);
        `"xkcd"` and `"garfield"` always serve whatever their front page currently shows, so
        this is ignored for them.

    Every story's headline is a fixed, source-derived name - `"XKCD"`, `"Garfield"`, or
    `"Calvin and Hobbes"` - never the strip's own (per-day) title, and no byline is set. Two
    comic sources commonly sit in the same section (e.g. a "Comics" section with both `"garfield"`
    and `"cah"`); a byline or a per-day dynamic headline (XKCD's own alt text, or a
    "<name> - <date>" fallback used in earlier versions of this provider) just repeated the same
    source name the headline already showed, or produced a needlessly long heading - neither
    adds anything a reader can use for a comic, unlike a byline on an RSS article (which
    distinguishes otherwise-anonymous entries from different feeds in the same section). XKCD's
    real per-day title is still available via its `alt` attribute on the embedded `<img>`, and
    its mouseover joke still renders as a caption underneath.

    The strip image itself is downloaded and inlined as a base64 `data:` URI rather than linked
    by remote URL, for two reasons: (1) gocomics.com requires the same browser-like headers for
    the *image* request as for the page request, and WeasyPrint (which fetches `<img src>` URLs
    itself while rendering the PDF) has no way to attach them; (2) it makes the rendered PDF
    self-contained - regenerating or re-delivering it later doesn't depend on the strip's image
    URL still being reachable.

    Before embedding, the fetched bytes are decoded and re-encoded as a clean, size-capped JPEG
    via Pillow - the same "decode, then adjust, then re-encode" pipeline remarkable_news's own Go
    tool runs (imaging.Decode + resize + imaging.Save with JPEGQuality, see module docstring).
    This isn't optional: embedding a source image unmodified - at whatever resolution, color
    mode/metadata, and *format* the source happened to serve that day - was reproduced to make
    WeasyPrint's PDF image embedding silently drop the *entire* story: no exception, no log line,
    just an empty gap where the story should have been, in an otherwise fully-rendered
    multi-hundred-page document. Three contributing factors were identified and all three are
    addressed by this step: (1) gocomics.com's CDN can serve a strip at print resolution
    (2800px+ wide) with no smaller variant requested (see `_MAX_IMAGE_DIMENSION`); (2) even at a
    source's *default* resolution, a lossless PNG re-encode of a dithered/gradient-heavy color
    strip is itself several times larger than the same content as JPEG - re-encoding as PNG
    alone was not enough to bring the payload down to a safe size; (3) arcamax.com's Garfield
    JPEGs ship CMYK-mode pixel data with a large embedded Photoshop/ICC metadata block. Any of
    these, combined with the hundreds of other images already in a full newspaper, was enough to
    trigger the failure. Re-encoding through Pillow bounds the pixel dimensions, normalizes color
    mode (e.g. CMYK -> RGB), and uses JPEG's lossy DCT compression - far more compact than PNG for
    this kind of photo-like, gradient-heavy content - regardless of what the source serves on a
    given day.
    """

    def __init__(self, comic_type: str, date: Optional[datetime.date] = None) -> None:
        if comic_type not in _COMIC_SOURCES:
            raise ValueError(
                f'Unknown comic_type "{comic_type}". Supported: '
                + ", ".join(sorted(_COMIC_SOURCES))
                + "."
            )
        self.comic_type = comic_type
        self.date = date

    def get_stories(self) -> List[Story]:
        source = _COMIC_SOURCES[self.comic_type]
        strip_date = self.date or datetime.date.today()
        page_url = source.page_url.format(date=strip_date)

        page_response = requests.get(
            page_url, headers=source.headers, timeout=_DEFAULT_TIMEOUT
        )
        page_response.raise_for_status()

        doc = lxml_html.fromstring(page_response.content)
        # Resolves every href/src in the tree against page_url in place, so the xpath lookups
        # below hand back absolute image URLs even where the page itself uses relative or
        # protocol-relative ones.
        doc.make_links_absolute(page_url)

        image_url = _first(doc.xpath(source.image_xpath))
        if not image_url:
            raise RuntimeError(
                f"Could not find today's {source.label} strip at {page_url} "
                "(the site's markup may have changed)."
            )

        subtitle = (
            _first(doc.xpath(source.subtitle_xpath)) if source.subtitle_xpath else None
        )

        image_response = requests.get(
            image_url, headers=source.headers, timeout=_DEFAULT_TIMEOUT
        )
        image_response.raise_for_status()

        image = Image.open(io.BytesIO(image_response.content))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        if max(image.size) > _MAX_IMAGE_DIMENSION:
            image.thumbnail((_MAX_IMAGE_DIMENSION, _MAX_IMAGE_DIMENSION), Image.LANCZOS)
        jpeg_buffer = io.BytesIO()
        image.save(jpeg_buffer, format="JPEG", quality=90)
        data_uri = f"data:image/jpeg;base64,{base64.b64encode(jpeg_buffer.getvalue()).decode('ascii')}"

        alt_text = escape(source.label)
        body_html = f'<img class="comic-strip" src="{data_uri}" alt="{alt_text}" />'
        if subtitle:
            body_html += f'<p class="comic-subtitle">{escape(subtitle)}</p>'

        return [
            Story(
                headline=source.label,
                body_html=(
                    _COMIC_CSS + f'<div class="comic-strip-body">{body_html}</div>'
                ),
                date=datetime.datetime.combine(strip_date, datetime.time()),
            )
        ]
