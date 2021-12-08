import requests
import feedparser
from typing import List
from readability import Document
import multiprocessing

from .story import Story
from .util import PlacementPreference
from .storyprovider import StoryProvider


class RSSFeedStoryProvider(StoryProvider):
    def __init__(
        self,
        title: str,
        link: str,
        rss_path: str,
        limit: int = 5,
        parallel: bool = True,
    ) -> None:
        self.title = title
        self.link = link
        self.limit = limit
        self.feed_url = rss_path
        self._parallel = parallel

    def get_stories(self, limit: int = 5) -> List[Story]:
        feed = feedparser.parse(self.feed_url)
        limit = min(limit, self.limit, len(feed.entries))
        title = Story(
            headline=f"<h1>{self.title}</h1>",
            body_html=f"""<a href={self.link}>{self.link}</a><br><br>""",
        )

        if limit == 0:
            print(f"Sad honk :/ No entries found for feed {self.feed_url}...")

        if self._parallel:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                stories = pool.map(self.parallelizable_request, feed.entries[:limit])
        else:
            stories = [self.parallelizable_request(e) for e in feed.entries[:limit]]

        stories.insert(0, title)

        return list(filter(None, stories))

    def parallelizable_request(self, entry):
        req = requests.get(entry["link"])
        if not req.ok:
            print(f"Honk! Couldn't grab content for {self.feed_url}")
            return None

        doc = Document(req.content)
        source = entry["link"].split(".")[1]
        story = Story(
            headline=f"<h2>{doc.title()}</h2>",
            body_html=doc.summary().replace("h2", "h3").replace("h1", "h2"),
            byline=source,
        )

        return story
