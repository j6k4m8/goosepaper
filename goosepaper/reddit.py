import feedparser
from typing import List

from .util import PlacementPreference
from .storyprovider import StoryProvider
from .story import Story


class RedditHeadlineStoryProvider(StoryProvider):
    def __init__(self, subreddit: str, limit: int = 20):
        self.limit = limit
        subreddit.lstrip("/")
        subreddit = subreddit[2:] if subreddit.startswith("r/") else subreddit
        self.subreddit = subreddit

    def get_stories(self, limit: int = 20) -> List[Story]:
        feed = feedparser.parse(f"https://www.reddit.com/r/{self.subreddit}.rss")
        limit = min(self.limit, len(feed.entries), limit)
        stories = []
        for entry in feed.entries[:limit]:
            try:
                author = entry.author
            except AttributeError:
                author = "A Reddit user"
            stories.append(
                Story(
                    headline=None,
                    body_text=entry.title,
                    byline=f"{author} in r/{self.subreddit}",
                    date=entry.updated_parsed,
                    placement_preference=PlacementPreference.SIDEBAR,
                )
            )
        return stories
