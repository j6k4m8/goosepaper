import datetime
import urllib.parse
from typing import List, Optional

import bs4
import feedparser
import requests
from readability import Document

from .imageutil import reencode_image_as_data_uri
from .storyprovider import StoryProvider
from ..story import Story
from ..version import __version__

RSS_BYLINE_MODES = {"all", "none", "first"}
RSS_BODY_SOURCES = {"auto", "content", "summary", "article"}

_IMAGE_FETCH_TIMEOUT = 20
# Matches a real newspaper column's rendered width - a source image well beyond this is pure
# waste, not extra quality (see _inline_remote_images' docstring for why capping it matters far
# more than that).
_MAX_IMAGE_DIMENSION = 1200


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
            try:
                story.body_html = _inline_remote_images(story.body_html)
            except Exception as err:
                print(
                    f"Sad honk :/ Couldn't process images for {story.headline!r}: {err}"
                )
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
    changed = False
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
            changed = True

    return container.decode_contents() if changed else body_html


def _inline_remote_images(body_html: str) -> str:
    """Re-fetches every remote `<img src="http(s)://...">` in body_html and inlines it as a
    base64 `data:` JPEG URI via `imageutil.reencode_image_as_data_uri`, instead of leaving it as
    a link to the original remote URL.

    Without this, a story's images are embedded exactly as the source served them, and WeasyPrint
    fetches each `<img src>` itself while rendering the PDF - with no control over what it gets.
    That's a known way for WeasyPrint to silently drop a story's image, or (once combined with
    the size/weight of everything else already in a full newspaper) sometimes the *entire* story
    - no exception, no log line, just a gap where it should have been (see imageutil's module
    docstring for the three contributing factors identified in practice).

    Verified against a real daily edition (110 stories, 26 feeds): 28 of 53 embedded images
    failed outright before this fix - multi-megapixel photos (up to 4000px, 500KB-1.4MB), a
    palette-mode PNG encoding photo-like content far less efficiently than JPEG, and WebP files
    (a format WeasyPrint's image backend can't decode at all, independent of size). This fix
    makes every one of those 53 images embed successfully (the one exception found live was an
    SVG - not a raster format Pillow can decode at all, left as its original link). Re-encoding
    every image through Pillow first, unconditionally, removes per-image failures as a variable -
    it does not by itself guarantee every story survives a very large, image-heavy edition (that
    also depends on the document's total combined weight, a separate, document-wide concern),
    but it's a necessary precondition for the ones that do.

    An image that fails to download or decode (network error, corrupt/unsupported data) is left
    as its original remote `<img>` tag rather than aborting the whole story - if that also fails
    later during rendering, it's no worse off than before this function existed; if it happens to
    render fine as-is, nothing was lost by trying.
    """
    if not body_html:
        return body_html

    soup = bs4.BeautifulSoup(body_html, "lxml")
    container = soup.body or soup
    changed = False
    for node in container.find_all("img"):
        src = node.get("src")
        if not src or not src.startswith(("http://", "https://")):
            continue
        try:
            response = requests.get(
                src,
                headers={"User-Agent": f"goosepaper/{__version__}"},
                timeout=_IMAGE_FETCH_TIMEOUT,
            )
            response.raise_for_status()
            node["src"] = reencode_image_as_data_uri(response.content, _MAX_IMAGE_DIMENSION)
            changed = True
        except Exception as err:
            print(
                f"Sad honk :/ Couldn't re-embed image {src}: {err} - leaving it as a remote link."
            )

    return container.decode_contents() if changed else body_html


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
