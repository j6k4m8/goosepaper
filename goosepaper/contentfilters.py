"""CSS-selector / regex cleanup rules for fetched article HTML, and title-based skip patterns.

Lets a plain RSS source config strip site-specific clutter (ad blocks, cookie banners, paywall
stubs, ...) or skip sponsored/paywalled entries by title - entirely as data
(`content_filters` / `skip_title_patterns` on the `"rss"` source type), no custom code required.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable

import bs4

_FLAG_CHARS = {
    "i": re.IGNORECASE,
    "s": re.DOTALL,
    "m": re.MULTILINE,
    "x": re.VERBOSE,
}


def _parse_flags(flags: str) -> int:
    combined = 0
    for ch in flags or "":
        combined |= _FLAG_CHARS.get(ch.lower(), 0)
    return combined


def apply_content_filters(html: str, filters: Iterable[Dict[str, Any]]) -> str:
    """Apply every filter in `filters` to `html`, in two passes: all `regex` filters first
    (against the raw string), then all `css` filters (against the parsed tree) - regex needs the
    raw string, css needs a parsed tree, so doing all of one before the other is simpler and just
    as correct as interleaving them in list order."""
    filters = list(filters or [])

    for filt in filters:
        if filt.get("type") == "regex":
            html = re.sub(filt["pattern"], "", html, flags=_parse_flags(filt.get("flags", "")))

    css_selectors = [filt["selector"] for filt in filters if filt.get("type") == "css"]
    if css_selectors:
        soup = bs4.BeautifulSoup(html, "lxml")
        for selector in css_selectors:
            for element in soup.select(selector):
                element.decompose()
        html = str(soup)

    return html


def should_skip_title(title: str, patterns: Iterable[str]) -> bool:
    title = title or ""
    return any(re.search(pattern, title, re.IGNORECASE) for pattern in patterns)
