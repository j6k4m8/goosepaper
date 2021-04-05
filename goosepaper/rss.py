import requests
import feedparser
from typing import List
from readability import Document
import multiprocessing
from datetime import datetime

from .story import Story
from .util import PlacementPreference
from .storyprovider import StoryProvider


class RSSFeedStoryProvider(StoryProvider):
    def __init__(self, rss_path: str, limit: int = 5) -> None:
        self.limit = limit
        self.feed_url = rss_path

    def get_story_date(self, entry):
        date = None
        dateStr = None
        if "pubDate" in entry:
            dateStr = entry["pubDate"]
        elif "updated" in entry:
            dateStr = entry["updated"]
        elif "published" in entry:
            dateStr = entry["published"]

        if dateStr:
            try:
                date = datetime.strptime(dateStr, "%a, %d %b %Y %H:%M:%S %z")
            except ValueError:
                pass #strange format, just skip it

        return date

    def get_stories(self, limit: int = 5, since = None) -> List[Story]:
        feed = feedparser.parse(self.feed_url)
        limit = min(self.limit, len(feed.entries))
        after = datetime.strptime(since, '%Y-%m-%d %H:%M:%S%z') if since else None

        with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
            stories = pool.map(self.parallelizable_request, feed.entries)

        if after:
            return list(
                filter(lambda story: story is not None and (
                    story.date and story.date > after
                ), stories)
            )

        return list(filter(lambda story: story is not None, stories))


    def parallelizable_request(self, entry):
        req = requests.get(entry["link"])
        if not req.ok:
            print(f"Honk! Couldn't grab content for {self.feed_url}")
            return None

        doc = Document(req.content)
        source = entry["link"].split(".")[1]
        date = self.get_story_date(entry)
        story = Story(doc.title(), body_html=doc.summary(), byline=source, date=date)

        return story

