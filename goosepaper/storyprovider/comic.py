"""Daily comic strip embedding - XKCD, plus any comic hosted on gocomics.com or arcamax.com.

The fetch mechanism (page URL, per-site HTTP headers, and the XPath used to find the strip's
<img> tag) was originally ported from evidlo/remarkable_news's per-comic systemd service files
(services/xkcd.service, services/cah.service, services/garfield.service) - see
https://github.com/evidlo/remarkable_news. That project renders comics onto a reMarkable's
suspend screen via a small Go CLI (`renews`) driven entirely by CLI flags (-url/-xpath/-header/
-strftime); this module reimplements the same lookups natively in Python for Goosepaper,
downloading the strip once as a Story rather than as a device-side background poller.

Unlike that per-comic origin, gocomics.com and arcamax.com each serve *every* strip in their
catalog (hundreds of them) through one identical URL/markup template - only the slug in the URL
differs per comic. So rather than hardcoding one `_ComicSource` per specific comic, there is one
entry per *site* here, and the specific comic is a runtime parameter (`comic_name`, the site's
own slug for it, e.g. "garfield" or "calvinandhobbes"). This was verified live against several
strips on each site before relying on it - see the module's test suite and PR history.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from html import escape
from typing import Callable, Dict, List, Literal, Optional

import requests
from lxml import html as lxml_html

from ..story import Story
from .imageutil import reencode_image_as_data_uri
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

# How many days to step backwards for a date-scoped source (gocomics.com) if the requested day's
# strip isn't up yet. Generation can run at any hour, and the source's own rollover time/timezone
# for "today's" strip isn't documented and isn't ours to guess (an earlier version of this module
# assumed US-Eastern; that assumption turned out unverifiable, and likely wrong - the publisher,
# Andrews McMeel Universal, is Kansas-City-based, i.e. Central time, not Eastern). Rather than
# predict the rollover, just detect a miss and retry the previous day - the most recent strip
# that actually exists is a better result than an empty section, regardless of what time of day
# or timezone generation happens to run in.
_MAX_FALLBACK_DAYS = 3

_COMIC_CSS = """
<style>
.comic-strip-body { text-align: center; }
.comic-strip-body img.comic-strip { max-width: 100%; height: auto; }
.comic-subtitle { font-size: 0.85em; font-style: italic; color: #444; margin-top: 0.4em; }
</style>
"""


def _first(values: List[str]) -> Optional[str]:
    return values[0] if values else None


def _extract_gocomics_label(doc: "lxml_html.HtmlElement") -> Optional[str]:
    """Pulls the comic's clean series name (e.g. "Pearls Before Swine", no date/author) out of
    the page's schema.org JSON-LD, rather than the visible <title>/og:title (both of which mix
    in the date and/or author - "Pearls Before Swine by Stephan Pastis for August 11, 2026")."""
    for raw in doc.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(data, dict) or data.get("@type") != "ComicStory":
            continue
        series = data.get("isPartOf")
        if isinstance(series, dict) and series.get("name"):
            return series["name"]
    return None


def _extract_arcamax_label(doc: "lxml_html.HtmlElement") -> Optional[str]:
    """arcamax.com's og:title meta tag is already the clean series name (e.g. "Beetle Bailey"),
    unlike its <title> tag which appends " | Comics | ArcaMax Publishing"."""
    return _first(doc.xpath('//meta[@property="og:title"]/@content'))


@dataclass(frozen=True)
class _ComicSource:
    # Fixed display label, for single-comic sources (xkcd) where there's nothing to derive.
    label: Optional[str] = None
    # For multi-comic sites (gocomics, arcamax): derives the label per-comic from the fetched
    # page, since one _ComicSource entry here covers every comic slug on that site. Exactly one
    # of `label` / `label_extractor` is set.
    label_extractor: Optional[Callable[["lxml_html.HtmlElement"], Optional[str]]] = None
    # May contain a {date} strftime-style placeholder (date-scoped sites) and/or a {slug}
    # placeholder (multi-comic sites, filled from comic_name). Extra/unused format placeholders
    # are simply not present in the template - str.format ignores unused kwargs.
    page_url: str = ""
    image_xpath: str = ""
    subtitle_xpath: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    # Whether DailyComicStoryProvider.__init__ must be given a comic_name for this source.
    requires_comic_name: bool = False


# Kept in sync with _COMIC_SOURCES' keys by hand - Literal can't be built from a dict's keys at
# type-check time, so this is the closest editors get to intellisense/hinting on comic_type.
ComicType = Literal["xkcd", "gocomics", "arcamax"]

_COMIC_SOURCES: Dict[ComicType, _ComicSource] = {
    "xkcd": _ComicSource(
        label="XKCD",
        page_url="https://xkcd.com",
        image_xpath='//div[@id="comic"]/img/@src',
        # The title attribute is the famous mouseover joke, shown as a caption under the strip.
        # (The strip's own dynamic title, in the alt attribute, is deliberately not used - see
        # the "headline" note in get_stories()'s docstring.)
        subtitle_xpath='//div[@id="comic"]/img/@title',
    ),
    "gocomics": _ComicSource(
        label_extractor=_extract_gocomics_label,
        page_url="https://www.gocomics.com/{slug}/{date:%Y}/{date:%m}/{date:%d}",
        image_xpath="//img[contains(@class, 'comic') and contains(@class, 'image')]/@src",
        # gocomics.com blocks non-browser-looking requests without these.
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0"
            ),
            "Accept-Language": "en",
            "Accept": "*/*",
        },
        requires_comic_name=True,
    ),
    "arcamax": _ComicSource(
        label_extractor=_extract_arcamax_label,
        page_url="https://www.arcamax.com/thefunnies/{slug}/",
        image_xpath='//img[@id="comic-zoom"]/@src',
        requires_comic_name=True,
    ),
}


class DailyComicStoryProvider(StoryProvider):
    """Downloads today's strip of a daily comic and embeds it as a single image Story.

    Constructor parameters:
      - `comic_type` (required): one of `"xkcd"`, `"gocomics"`, `"arcamax"`. No default - a
        config that forgets it should fail loudly instead of silently always fetching XKCD.
      - `comic_name` (required for `"gocomics"`/`"arcamax"`, rejected for `"xkcd"`): the comic's
        own slug on that site, exactly as it appears in the site's URL - e.g. `"garfield"` or
        `"calvinandhobbes"` for gocomics.com, `"beetlebailey"` for arcamax.com. `"xkcd"` only
        ever serves one comic, so it takes no `comic_name`.
      - `date` (optional, default today): which day's strip to fetch. Only meaningful for
        `"gocomics"`, whose page URL is date-scoped (`gocomics.com/<slug>/YYYY/MM/DD`); `"xkcd"`
        and `"arcamax"` always serve whatever their front page currently shows, so this is
        ignored for them.

    Every story's headline is a fixed, source-derived name - never the strip's own (per-day)
    title, and no byline is set. Two comic sources commonly sit in the same section (e.g. a
    "Comics" section with both a gocomics and an arcamax entry); a byline or a per-day dynamic
    headline (XKCD's own alt text, or a "<name> - <date>" fallback used in earlier versions of
    this provider) just repeated the same source name the headline already showed, or produced a
    needlessly long heading - neither adds anything a reader can use for a comic, unlike a byline
    on an RSS article (which distinguishes otherwise-anonymous entries from different feeds in
    the same section). For `"xkcd"` the label is fixed to `"XKCD"`; its real per-day title is
    still available via the embedded image's `alt` attribute, and its mouseover joke still
    renders as a caption underneath. For `"gocomics"`/`"arcamax"`, the label is instead read off
    the fetched page itself (see `_extract_gocomics_label`/`_extract_arcamax_label`) - one
    `_ComicSource` entry covers every comic on that site, so there's no per-comic label to
    hardcode.

    The strip image itself is downloaded and inlined as a base64 `data:` URI rather than linked
    by remote URL, for two reasons: (1) gocomics.com requires the same browser-like headers for
    the *image* request as for the page request, and WeasyPrint (which fetches `<img src>` URLs
    itself while rendering the PDF) has no way to attach them; (2) it makes the rendered PDF
    self-contained - regenerating or re-delivering it later doesn't depend on the strip's image
    URL still being reachable.

    Before embedding, the fetched bytes are decoded and re-encoded as a clean, size-capped JPEG
    via `imageutil.reencode_image_as_data_uri` - the same "decode, then adjust, then re-encode"
    pipeline remarkable_news's own Go tool runs (imaging.Decode + resize + imaging.Save with
    JPEGQuality). This isn't optional: embedding a source image unmodified - at whatever
    resolution, color mode/metadata, and *format* the source happened to serve that day - was
    reproduced to make WeasyPrint's PDF image embedding silently drop the *entire* story: no
    exception, no log line, just an empty gap where the story should have been, in an otherwise
    fully-rendered multi-hundred-page document. Three contributing factors were identified, all
    addressed by imageutil's re-encode step (see its own module docstring for the general case):
    (1) gocomics.com's CDN can serve a strip at print resolution (2800px+ wide) with no smaller
    variant requested; (2) even at a source's *default* resolution, a lossless PNG re-encode of a
    dithered/gradient-heavy color strip is several times larger than the same content as JPEG;
    (3) arcamax.com's Garfield JPEGs ship CMYK-mode pixel data with a large embedded
    Photoshop/ICC metadata block. Any of these, combined with the hundreds of other images
    already in a full newspaper, was enough to trigger the failure.
    """

    def __init__(
        self,
        comic_type: ComicType,
        comic_name: Optional[str] = None,
        date: Optional[datetime.date] = None,
    ) -> None:
        # Literal[...] above only helps editors/type-checkers at call sites written directly in
        # Python - config-driven callers (see util.py) pass a plain str straight from JSON, so
        # this runtime check is still the only thing actually catching a bad value from those.
        if comic_type not in _COMIC_SOURCES:
            raise ValueError(
                f'Unknown comic_type "{comic_type}". Supported: '
                + ", ".join(sorted(_COMIC_SOURCES))
                + "."
            )
        source = _COMIC_SOURCES[comic_type]
        if source.requires_comic_name and not comic_name:
            raise ValueError(
                f'comic_type "{comic_type}" requires a comic_name - the comic\'s own slug on '
                'that site, e.g. "garfield" or "calvinandhobbes".'
            )
        if not source.requires_comic_name and comic_name:
            raise ValueError(f'comic_type "{comic_type}" does not take a comic_name.')
        self.comic_type = comic_type
        self.comic_name = comic_name
        self.date = date

    def get_stories(self) -> List[Story]:
        source = _COMIC_SOURCES[self.comic_type]
        strip_date = self.date or datetime.date.today()
        requested_page_url = source.page_url.format(date=strip_date, slug=self.comic_name)
        # Only worth retrying earlier dates when the URL is actually date-scoped - for
        # xkcd/arcamax, every attempt would just re-fetch the same "current front page" URL.
        is_date_scoped = "{date" in source.page_url
        max_attempts = (_MAX_FALLBACK_DAYS + 1) if is_date_scoped else 1

        doc = None
        page_url = requested_page_url
        image_url: Optional[str] = None
        for offset in range(max_attempts):
            candidate_date = strip_date - datetime.timedelta(days=offset)
            page_url = source.page_url.format(date=candidate_date, slug=self.comic_name)

            page_response = requests.get(
                page_url, headers=source.headers, timeout=_DEFAULT_TIMEOUT
            )
            page_response.raise_for_status()

            doc = lxml_html.fromstring(page_response.content)
            # Resolves every href/src in the tree against page_url in place, so the xpath
            # lookups below hand back absolute image URLs even where the page itself uses
            # relative or protocol-relative ones.
            doc.make_links_absolute(page_url)

            image_url = _first(doc.xpath(source.image_xpath))
            if image_url:
                if offset:
                    print(
                        f"Sad honk :/ No strip found yet for {self.comic_name or self.comic_type} "
                        f"on {strip_date} (checked {requested_page_url}); using "
                        f"{candidate_date}'s strip instead."
                    )
                break

        if not image_url:
            raise RuntimeError(
                f"Could not find today's strip at {requested_page_url} "
                "(the site's markup may have changed)."
            )

        if source.label is not None:
            label = source.label
        else:
            label = source.label_extractor(doc) if source.label_extractor else None
            if not label:
                raise RuntimeError(
                    f"Could not determine the comic's display name at {page_url} "
                    "(the site's markup may have changed)."
                )

        subtitle = (
            _first(doc.xpath(source.subtitle_xpath)) if source.subtitle_xpath else None
        )

        image_response = requests.get(
            image_url, headers=source.headers, timeout=_DEFAULT_TIMEOUT
        )
        image_response.raise_for_status()

        data_uri = reencode_image_as_data_uri(image_response.content, _MAX_IMAGE_DIMENSION)

        alt_text = escape(label)
        body_html = f'<img class="comic-strip" src="{data_uri}" alt="{alt_text}" />'
        if subtitle:
            body_html += f'<p class="comic-subtitle">{escape(subtitle)}</p>'

        return [
            Story(
                headline=label,
                body_html=(
                    _COMIC_CSS + f'<div class="comic-strip-body">{body_html}</div>'
                ),
                date=datetime.datetime.combine(strip_date, datetime.time()),
            )
        ]
