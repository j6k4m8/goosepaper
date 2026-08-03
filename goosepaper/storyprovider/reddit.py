from typing import List
import datetime
import feedparser
import re
import requests
import time

from ..util import PlacementPreference
from .storyprovider import StoryProvider
from ..story import Story
from ..version import __version__


REDDIT_USER_AGENT = (
    f"python:goosepaper:{__version__} "
    "(by /u/j6k4m8; +https://github.com/j6k4m8/goosepaper)"
)
MAX_REDDIT_BACKOFF_SECONDS = 60
REDDIT_MULTI_SUB_ORDERS = {"date", "subreddit"}


class RedditHeadlineStoryProvider(StoryProvider):
    def __init__(
        self,
        subreddit: str,
        limit: int = 20,
        since_days_ago: int = None,
        max_retries: int = 2,
        backoff_seconds: float = 2.0,
        multi_sub_order: str = "date",
    ):
        if multi_sub_order not in REDDIT_MULTI_SUB_ORDERS:
            raise ValueError(
                'Reddit multi_sub_order must be one of "date" or "subreddit".'
            )
        self.limit = limit
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.multi_sub_order = multi_sub_order
        self._since = (
            datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
            if since_days_ago
            else None
        )
        self.subreddits = _normalize_subreddits(subreddit)
        self.subreddit = "+".join(self.subreddits)

    def get_stories(self) -> List[Story]:
        response = self._fetch_feed_response()
        feed = feedparser.parse(response.content)
        limit = min(self.limit, len(feed.entries))
        stories = []
        for entry in feed.entries:
            try:
                author = entry.author
            except AttributeError:
                author = "A Reddit user"

            date = datetime.datetime(*entry.updated_parsed[:6])
            if self._since is not None and date < self._since:
                continue

            subreddit = _entry_subreddit(entry, default=self.subreddit)
            story = Story(
                headline="",
                body_text=str(entry.title),
                byline=f"{author} in r/{subreddit}",
                date=date,
                placement_preference=PlacementPreference.SIDEBAR,
                section_title="Reddit",
                short_form=True,
            )
            stories.append((subreddit, story))
            if len(stories) >= limit:
                break

        return [
            story
            for subreddit, story in self._ordered_stories(stories)
        ]

    def _ordered_stories(self, stories):
        if self.multi_sub_order != "subreddit" or len(self.subreddits) < 2:
            return stories

        ordered_stories = []
        remaining_stories = list(stories)
        for expected_subreddit in self.subreddits:
            matched = [
                (subreddit, story)
                for subreddit, story in remaining_stories
                if subreddit.lower() == expected_subreddit.lower()
            ]
            ordered_stories.extend(matched)
            remaining_stories = [
                (subreddit, story)
                for subreddit, story in remaining_stories
                if subreddit.lower() != expected_subreddit.lower()
            ]
        return ordered_stories + remaining_stories

    def _fetch_feed_response(self):
        for attempt in range(self.max_retries + 1):
            response = requests.get(
                f"https://www.reddit.com/r/{self.subreddit}.rss",
                params={"limit": self.limit},
                headers={"User-Agent": REDDIT_USER_AGENT},
                timeout=20,
            )
            if response.status_code != 429 or attempt >= self.max_retries:
                response.raise_for_status()
                return response

            time.sleep(_reddit_backoff_seconds(response, self.backoff_seconds))

        return response


def _normalize_subreddits(subreddit: str) -> List[str]:
    subreddits = []
    for part in subreddit.split("+"):
        normalized = part.strip().lstrip("/").rstrip("/")
        if normalized.startswith("r/"):
            normalized = normalized[2:]
        if not normalized:
            raise ValueError("Reddit subreddit cannot be empty.")
        subreddits.append(normalized)
    return subreddits


def _entry_subreddit(entry, default: str) -> str:
    link = _entry_value(entry, "link")
    if link:
        match = re.search(r"/r/([^/]+)/", link, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return default


def _entry_value(entry, key: str):
    if hasattr(entry, "get"):
        return entry.get(key)
    return getattr(entry, key, None)


def _reddit_backoff_seconds(response, fallback: float) -> float:
    retry_after = _header_float(response, "Retry-After", "retry-after")
    if retry_after is not None:
        return _bounded_backoff(retry_after)

    reset_after = _header_float(
        response,
        "x-ratelimit-reset",
        "X-Ratelimit-Reset",
        "X-RateLimit-Reset",
    )
    if reset_after is not None:
        return _bounded_backoff(reset_after)

    return _bounded_backoff(fallback)


def _header_float(response, *names: str):
    for name in names:
        value = response.headers.get(name)
        if value is None:
            continue
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _bounded_backoff(seconds: float) -> float:
    return min(max(seconds, 1.0), MAX_REDDIT_BACKOFF_SECONDS)
