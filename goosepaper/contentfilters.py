"""CSS-selector / regex cleanup rules for fetched article HTML, and title-based skip/accept
patterns.

Lets a plain RSS source config strip site-specific clutter (ad blocks, cookie banners, paywall
stubs, ...) or skip sponsored/paywalled entries by title - entirely as data
(`content_skip_filters` / `skip_title_patterns` on the `"rss"` source type), no custom code
required. `content_accept_filters` / `accept_title_patterns` are the inverse: narrow down to just
the real article container, or keep only entries about a topic you actually want (e.g. one
company's name from an otherwise general business feed) - useful when the junk is unpredictable
but you know exactly where or what the real content is.
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


def apply_content_skip_filters(html: str, filters: Iterable[Dict[str, Any]]) -> str:
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


def apply_content_accept_filters(html: str, filters: Iterable[Dict[str, Any]]) -> str:
    """Narrow `html` down to just one container: try each filter's `selector` in list order,
    keep the first one that matches an element (`select_one`), and replace the whole tree with
    just that element's contents. Only CSS selectors are supported - a regex "accept" would just
    reduce the story to whatever static phrase the pattern matches, not coherent prose, so unlike
    `content_skip_filters` there's no `type` field here.

    Falls through to the original `html` unchanged if no filter matches - an accept filter that
    misses its target should never zero out an article, only skip filters remove content."""
    for filt in filters or []:
        soup = bs4.BeautifulSoup(html, "lxml")
        match = soup.select_one(filt["selector"])
        if match is not None:
            return str(match)
    return html


def should_accept_title(title: str, patterns: Iterable[str]) -> bool:
    """True if `patterns` is empty (nothing to restrict to, so every title is accepted) or
    `title` matches at least one - the allowlist counterpart to `should_skip_title`'s denylist,
    e.g. keeping only a general feed's entries that mention one company's name."""
    patterns = list(patterns or [])
    if not patterns:
        return True
    title = title or ""
    return any(re.search(pattern, title, re.IGNORECASE) for pattern in patterns)
