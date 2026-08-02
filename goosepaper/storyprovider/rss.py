import datetime
import re
import urllib.parse
from typing import List, Optional

import bs4
import feedparser
import requests
from readability import Document

from .storyprovider import StoryProvider
from ..story import Story
from ..version import __version__

RSS_BYLINE_MODES = {"all", "none", "first"}
RSS_BODY_SOURCES = {"auto", "content", "summary", "article"}


class RSSFeedStoryProvider(StoryProvider):
    def __init__(
        self,
        rss_path: str,
        limit: int = 5,
        since_days_ago: int = None,
        byline: str = "all",
        body_source: str = "auto",
        prefer_feed_title: bool = False,
    ) -> None:
        if byline not in RSS_BYLINE_MODES:
            raise ValueError(
                'RSS byline must be one of "all", "none", or "first".'
            )
        if body_source not in RSS_BODY_SOURCES:
            raise ValueError(
                'RSS body_source must be one of "auto", "content", '
                '"summary", or "article".'
            )
        self.limit = limit
        self.feed_url = rss_path
        self.byline_mode = byline
        self.body_source = body_source
        self.prefer_feed_title = prefer_feed_title
        self._since = (
            datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
            if since_days_ago
            else None
        )

    def get_stories(self) -> List[Story]:
        feed = feedparser.parse(self.feed_url)
        limit = min(self.limit, len(feed.entries))
        if limit == 0:
            print(f"Sad honk :/ No entries found for feed {self.feed_url}...")

        stories = []
        for entry in feed.entries:
            date = datetime.datetime(*entry.updated_parsed[:6])
            if self._since is not None and date < self._since:
                continue

            source = _entry_source(entry, self.feed_url)
            story = _story_from_entry(
                entry,
                source,
                date,
                body_source=self.body_source,
                prefer_feed_title=self.prefer_feed_title,
            )

            if story is None:
                continue
            if self.byline_mode == "none":
                story.byline = None
            elif self.byline_mode == "first" and stories:
                story.byline = None

            stories.append(story)
            if len(stories) >= limit:
                break

        return list(filter(None, stories))


def _story_from_entry(
    entry,
    source: str,
    date: datetime.datetime,
    body_source: str = "auto",
    prefer_feed_title: bool = False,
) -> Optional[Story]:
    try:
        return _story_from_entry_unsafe(entry, source, date, body_source=body_source)
    except Exception as err:
        print(
            f"Sad honk :/ Skipping {entry.get('link', entry.get('title'))}: {err}"
        )
        return None


def _story_from_entry_unsafe(
    entry,
    source: str,
    date: datetime.datetime,
    body_source: str = "auto",
) -> Story:
    if body_source == "summary":
        return Story(
            entry["title"],
            body_html=_entry_feed_body(entry, preferred="summary"),
            byline=source,
            date=date,
        )

    embedded_content = _entry_embedded_content(entry)
    if embedded_content and body_source != "article":
        return Story(
            entry["title"],
            body_html=embedded_content,
            byline=source,
            date=date,
        )

    link = entry.get("link")
    fallback_body_html = _entry_feed_body(entry, preferred="content")

    if body_source == "content":
        return Story(
            entry["title"],
            body_html=fallback_body_html,
            byline=source,
            date=date,
        )

    if not link:
        return Story(
            entry["title"],
            body_html=fallback_body_html,
            byline=source,
            date=date,
        )

    req = requests.get(
        link,
        headers={"User-Agent": f"goosepaper/{__version__}"},
    )
    if not req.ok:
        return Story(
            entry["title"],
            body_html=fallback_body_html,
            byline=source,
            date=date,
        )

    return _story_from_response(
        entry,
        req,
        source,
        date,
        fallback_body_html=fallback_body_html,
        prefer_feed_title=prefer_feed_title,
    )


def _story_from_response(
    entry,
    response,
    source: str,
    date: datetime.datetime,
    fallback_body_html: str = "",
    prefer_feed_title: bool = False,
) -> Story:
    page_text = response.text
    if not page_text:
        page_text = response.content.decode(
            response.encoding or "utf-8",
            errors="replace",
        )

    try:
        doc = Document(page_text)
        # readability's own title extraction is unreliable on some sites (e.g. it
        # returns just the site name for every article on some blogs); the feed's
        # own <title> is usually accurate, so let callers prefer it outright.
        headline = entry["title"] if prefer_feed_title else (doc.title() or entry["title"])
        body_html = doc.summary() or fallback_body_html
        body_html = _make_urls_absolute(body_html, response.url)
        body_html = _strip_duplicate_leading_heading(body_html, headline)
    except Exception:
        headline = entry["title"]
        body_html = fallback_body_html

    return Story(
        headline,
        body_html=body_html,
        byline=source,
        date=date,
    )


def _make_urls_absolute(body_html: str, base_url: str) -> str:
    """Readability's extracted body_html can carry relative URLs straight from the source page's
    own markup (`<img src="/assets/img/foo.webp">`, relative `<a href>`, protocol-relative
    `<img src="//images.example.com/foo.jpg">`, ...). goosepaper renders the whole newspaper -
    every story from every source, concatenated - as a single HTML document with one `base_url`
    (see `Goosepaper.to_pdf`, which sets it to the local filesystem's `cwd` - there's no single
    correct base for a multi-origin document), so a relative URL that arrives this way resolves
    against the wrong thing and silently fails - images most visibly ("Failed to load image at
    'file:///assets/img/foo.webp': ... No such file or directory" in the log). Absolutize against
    the article's own URL here, at extraction time, while that's still known and correct for this
    specific story.
    """
    if not body_html or not base_url:
        return body_html

    soup = bs4.BeautifulSoup(body_html, "lxml")
    container = soup.body or soup
    for tag_name, attr in (("img", "src"), ("source", "src"), ("a", "href")):
        for node in container.find_all(tag_name):
            value = node.get(attr)
            # Only a `scheme` (e.g. "https") makes a URL truly absolute. `.netloc` is *not*
            # enough: protocol-relative URLs ("//host/path") also parse with a netloc but no
            # scheme, so checking netloc alone left them untouched here - they'd then get
            # resolved later against the newspaper's file:// base_url instead, producing
            # broken "file://host/path" URLs.
            if not value or value.startswith("data:") or urllib.parse.urlparse(value).scheme:
                continue
            node[attr] = urllib.parse.urljoin(base_url, value)

    # Always re-serialize via decode_contents(), even when nothing needed absolutizing - not an
    # optimization to skip. bs4's lxml parser wraps whatever it's given in a synthetic
    # <html><body> (readability's own doc.summary() output already looks exactly like a full
    # document, so lxml has no reason to suspect it's a fragment); container.decode_contents()
    # is what strips that wrapper back off. Returning the untouched input on a "nothing to
    # change" run - as the original version of this function did - let that synthetic
    # <html><body> leak straight into the final newspaper's body_html verbatim whenever an
    # article happened to have zero relative URLs (i.e. every link/image on the page was already
    # absolute - common, not an edge case). A second <html> tag appearing mid-document is enough
    # to confuse WeasyPrint's parser into silently dropping everything from that point until it
    # resyncs, sometimes taking an entire story down with it.
    return container.decode_contents()


_TITLE_SUFFIX_RE = re.compile(r"\s*[-|–—]\s*[^-|–—]+$")
# Tolerates a short "kicker"/eyebrow label before the duplicate heading (e.g. The Register's
# leading <p class="kicker">ai and ml</p>) without mistaking it for real leading body content.
_MAX_PRECEDING_CHROME_CHARS = 40


def _normalize_heading_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _heading_matches_headline(heading_text: str, headline: str) -> bool:
    """Loosely compares a body-embedded heading against the resolved headline: an exact
    (normalized) match, or a match once a trailing " - Sitename" / " | Sitename" is stripped off
    the headline - readability's doc.title() commonly keeps a site-name suffix from the page's
    own <title> tag (e.g. MacRumors: "... - MacRumors"), but the embedded body heading itself
    usually doesn't carry it.
    """
    normalized_heading = _normalize_heading_text(heading_text)
    if not normalized_heading:
        return False
    if normalized_heading == _normalize_heading_text(headline):
        return True
    stripped_headline = _TITLE_SUFFIX_RE.sub("", headline or "")
    return bool(stripped_headline) and normalized_heading == _normalize_heading_text(
        stripped_headline
    )


def _strip_duplicate_leading_heading(body_html: str, headline: str) -> str:
    """Some sites' article markup repeats the headline inside the same container readability
    identifies as "the article body" - e.g. Engadget's `<h1 class="title-gallery">`, The
    Register's and MacRumors' equivalents as an actual heading tag, or heise's auto-generated
    table-of-contents widget (`<a-collapse class="a-toc">...<li><span aria-current="page">` -
    the current page's own TOC entry, holding the plain headline text with no heading tag at
    all). readability's extraction has no way to know any of these duplicates the page title
    rather than being real body content, so it stays in `doc.summary()`'s output; the story then
    renders with the headline twice - once from Story's own explicit headline, once again as the
    first thing inside the body (as a spurious bullet/number in the TOC-widget case, since it's a
    list item).

    Strips a leading element whose full text matches `headline` (see `_heading_matches_headline`)
    to avoid that - deliberately not restricted to heading tags, since a duplicate can just as
    well be a `<span>`/`<li>` inside a non-heading wrapper. `.descendants` visits a tag before its
    own text (a `<span>`'s text is a *separate*, later descendant of its parent), so matching at
    the tag level and returning immediately never lets a matched element's own text reach the
    chrome-budget count below - only text that is *not* part of the eventual match can ever count
    as "preceding chrome" toward `_MAX_PRECEDING_CHROME_CHARS` (enough for a short kicker/eyebrow
    label, not a real paragraph), so a duplicate deeper in genuine body content, even one that
    happens to repeat the headline verbatim, is still left alone. Matching at the tag level also
    means the *outermost* matching wrapper is the one removed (e.g. the whole `<a-collapse>` TOC
    widget, not just the innermost `<span>`) - stripping only the innermost text node would leave
    an empty `<li>` behind, and its bullet/number would still show up in the rendered PDF.
    """
    if not headline or not body_html:
        return body_html

    soup = bs4.BeautifulSoup(body_html, "lxml")
    container = soup.body or soup
    preceding_chars = 0

    for node in container.descendants:
        if isinstance(node, bs4.Tag):
            if _heading_matches_headline(node.get_text(), headline):
                node.decompose()
                # decode_contents(), not str(container): `container` came from `soup.body`, and
                # bs4's lxml parser always wraps a fragment in a synthetic <html><body> - str()-
                # ing it back would leave body_html wrapped in a literal <body> tag it never had
                # before, nested inside whatever real <body>/<div> the caller later embeds it in.
                return container.decode_contents()
            continue
        if isinstance(node, bs4.NavigableString):
            preceding_chars += len(node.strip())
            if preceding_chars > _MAX_PRECEDING_CHROME_CHARS:
                return body_html
            continue

    return body_html


def _entry_source(entry, feed_url: str) -> str:
    source_url = entry.get("link") or feed_url
    return urllib.parse.urlparse(source_url).netloc or source_url


def _entry_embedded_content(entry) -> Optional[str]:
    for content_block in entry.get("content", []):
        if not isinstance(content_block, dict):
            continue
        value = content_block.get("value")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _entry_summary(entry) -> str:
    return entry.get("summary") or entry.get("description") or ""


def _entry_feed_body(entry, preferred: str = "content") -> str:
    if preferred == "summary":
        return _entry_summary(entry) or (_entry_embedded_content(entry) or "")
    embedded_content = _entry_embedded_content(entry)
    if embedded_content:
        return embedded_content
    return _entry_summary(entry)
