import datetime
import urllib.parse
from typing import List

import feedparser
import requests
from readability import Document

from .storyprovider import StoryProvider
from ..story import Story
from ..version import __version__


class RSSFeedStoryProvider(StoryProvider):
    def __init__(
        self,
        rss_path: str,
        limit: int = 5,
        since_days_ago: int = None,
    ) -> None:
        self.limit = limit
        self.feed_url = rss_path
        self._since = (
            datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
            if since_days_ago
            else None
        )

    def get_stories(self, limit: int = 5, **kwargs) -> List[Story]:
        feed = feedparser.parse(self.feed_url)
        limit = min(limit, self.limit, len(feed.entries))
        if limit == 0:
            print(f"Sad honk :/ No entries found for feed {self.feed_url}...")

        stories = []
        for entry in feed.entries:
            date = datetime.datetime(*entry.updated_parsed[:6])
            if self._since is not None and date < self._since:
                continue

            req = requests.get(
                entry["link"],
                headers={"User-Agent": f"goosepaper/{__version__}"},
            )
            # Source is the URL root:
            source = urllib.parse.urlparse(entry["link"]).netloc
            if not req.ok:
                # Just return the headline content:
                story = Story(
                    entry["title"],
                    body_html=entry.get("summary", ""),
                    byline=source,
                    date=date,
                )
            else:
                story = _story_from_response(entry, req, source, date)

            stories.append(story)
            if len(stories) >= limit:
                break

        return list(filter(None, stories))


def _story_from_response(entry, response, source: str, date: datetime.datetime) -> Story:
    page_text = response.text
    if not page_text:
        page_text = response.content.decode(
            response.encoding or "utf-8",
            errors="replace",
        )

    try:
        doc = Document(page_text)
        headline = doc.title() or entry["title"]
        body_html = doc.summary() or entry.get("summary", "")
    except Exception:
        headline = entry["title"]
        body_html = entry.get("summary", "")

    return Story(
        headline,
        body_html=body_html,
        byline=source,
        date=date,
    )
