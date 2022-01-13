import requests
import feedparser
from typing import List
from readability import Document
import multiprocessing

from .story import Story
from .storyprovider import StoryProvider


def parallelizable_request(entry):
    req = requests.get(entry["link"])
    if not req.ok:
        print(f"Honk! Couldn't get content for {entry['link']}")
        return None

    doc = Document(req.content)
    source = entry["link"].split(".")[1]
    story = Story(doc.title(), body_html=doc.summary(), byline=source)

    return story


class RSSFeedStoryProvider(StoryProvider):
    def __init__(
        self,
        rss_path: str,
        limit: int = 5,
        parallel: bool = True,
    ) -> None:
        self.limit = limit
        self.feed_url = rss_path
        self._parallel = parallel

    def get_stories(self, limit: int = 5) -> List[Story]:
        feed = feedparser.parse(self.feed_url)
        limit = min(limit, self.limit, len(feed.entries))
        if limit == 0:
            print(f"Sad honk :/ No entries found for feed {self.feed_url}...")

        if self._parallel:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                stories = pool.map(
                    parallelizable_request,
                    feed.entries[:limit],
                )
        else:
            stories = [parallelizable_request(e) for e in feed.entries[:limit]]

        return list(filter(None, stories))
