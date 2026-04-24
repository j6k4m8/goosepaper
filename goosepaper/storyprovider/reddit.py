from typing import List
import datetime
import feedparser
import requests

from ..util import PlacementPreference
from .storyprovider import StoryProvider
from ..story import Story
from ..version import __version__


class RedditHeadlineStoryProvider(StoryProvider):
    def __init__(self, subreddit: str, limit: int = 20, since_days_ago: int = None):
        self.limit = limit
        self._since = (
            datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
            if since_days_ago
            else None
        )
        subreddit = subreddit.strip().lstrip("/").rstrip("/")
        subreddit = subreddit[2:] if subreddit.startswith("r/") else subreddit
        self.subreddit = subreddit

    def get_stories(self, limit: int = 20, **kwargs) -> List[Story]:
        response = requests.get(
            f"https://www.reddit.com/r/{self.subreddit}.rss",
            headers={"User-Agent": f"goosepaper/{__version__}"},
            timeout=20,
        )
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        limit = min(self.limit, len(feed.entries), limit)
        stories = []
        for entry in feed.entries:
            try:
                author = entry.author
            except AttributeError:
                author = "A Reddit user"

            date = datetime.datetime(*entry.updated_parsed[:6])
            if self._since is not None and date < self._since:
                continue

            stories.append(
                Story(
                    headline="",
                    body_text=str(entry.title),
                    byline=f"{author} in r/{self.subreddit}",
                    date=date,
                    placement_preference=PlacementPreference.SIDEBAR,
                )
            )
            if len(stories) >= limit:
                break

        return stories
