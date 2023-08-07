import datetime
import feedparser
from typing import List

from .storyprovider import StoryProvider
from ..story import Story


class MastodonStoryProvider(StoryProvider):
    def __init__(
        self,
        server: str,
        username: str,
        limit: int = 5,
        since_days_ago: int = None,
    ) -> None:
        self.limit = limit
        self.username = username
        self.feed_url = server.rstrip("/") + "/@" + username.lstrip("@") + ".rss"
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
            date = datetime.datetime(*entry.published_parsed[:6])
            if self._since is not None and date < self._since:
                continue

            # Just return the headline content:
            story = Story(
                "@"
                + self.username.lstrip("@")
                + " at "
                + date.strftime("%Y-%m-%d %H:%M"),
                body_html=entry["summary"],
                byline=self.username,
                date=date,
            )

            stories.append(story)
            if len(stories) >= limit:
                break

        return list(filter(None, stories))
