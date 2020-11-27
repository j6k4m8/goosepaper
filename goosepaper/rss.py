import requests
import feedparser
from typing import List
from readability import Document

from .story import Story
from .util import PlacementPreference
from .storyprovider import StoryProvider


class RSSFeedStoryProvider(StoryProvider):
    def __init__(self, rss_path: str, limit: int = 5) -> None:
        self.limit = limit
        self.feed_url = rss_path

    def get_stories(self, limit: int = 5) -> List[Story]:
        feed = feedparser.parse(self.feed_url)
        limit = min(self.limit, len(feed.entries))
        stories = []

        for entry in feed.entries[:limit]:
            if "link" in entry.keys():
                req = requests.get(entry["link"])
                if not req.ok:
                    print(f"Honk! Couldn't grab content for {self.feed_url}")
                    continue

                doc = Document(req.content)
                source = entry["link"].split(".")[1]
                stories.append(
                    Story(doc.title(), body_html=doc.summary(), byline=source)
                )

        return stories
