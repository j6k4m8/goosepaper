import requests
import feedparser
from typing import List
from readability import Document
import multiprocessing

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

        with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
            stories = pool.map(self.parallelizable_request, feed.entries)

        return list(filter(None, stories))

    def parallelizable_request(self, entry):
        req = requests.get(entry["link"])
        if not req.ok:
            print(f"Honk! Couldn't grab content for {self.feed_url}")
            return None

        doc = Document(req.content)
        source = entry["link"].split(".")[1]
        story = Story(doc.title(), body_html=doc.summary(), byline=source) 

        return story

