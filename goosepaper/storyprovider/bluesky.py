import datetime
import re
from html import escape
from typing import List, Optional

import requests

from .storyprovider import StoryProvider
from ..story import Story
from ..version import __version__

_PUBLIC_APPVIEW_URL = "https://public.api.bsky.app"
_AUTHOR_FEED_PATH = "/xrpc/app.bsky.feed.getAuthorFeed"


class BlueskyStoryProvider(StoryProvider):
    def __init__(
        self,
        username: str,
        limit: int = 5,
        since_days_ago: int = None,
        include_replies: bool = True,
    ) -> None:
        self.limit = limit
        self.username = username.lstrip("@")
        self.include_replies = include_replies
        self.feed_filter = (
            "posts_with_replies" if include_replies else "posts_no_replies"
        )
        self.feed_url = _PUBLIC_APPVIEW_URL + _AUTHOR_FEED_PATH
        self._since = (
            datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            - datetime.timedelta(days=since_days_ago)
            if since_days_ago
            else None
        )

    def get_stories(self, limit: int = 5, **kwargs) -> List[Story]:
        response = requests.get(
            self.feed_url,
            params={
                "actor": self.username,
                "filter": self.feed_filter,
                "limit": min(self.limit, limit),
            },
            headers={"User-Agent": f"goosepaper/{__version__}"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        stories = []
        for feed_item in payload.get("feed", []):
            story = _story_from_feed_item(feed_item, requested_handle=self.username)
            if story is None:
                continue
            if self._since is not None and story.date is not None and story.date < self._since:
                continue

            stories.append(story)
            if len(stories) >= min(self.limit, limit):
                break

        return stories


def _story_from_feed_item(
    feed_item: dict,
    requested_handle: str,
) -> Optional[Story]:
    reason = feed_item.get("reason") or {}
    if reason.get("$type") == "app.bsky.feed.defs#reasonRepost":
        return None

    post = feed_item.get("post") or {}
    author = post.get("author") or {}
    record = post.get("record") or {}
    post_text = record.get("text") or ""
    handle = (author.get("handle") or requested_handle).lstrip("@")
    display_name = author.get("displayName") or ("@" + handle)
    date = _parse_bsky_datetime(record.get("createdAt") or post.get("indexedAt"))
    headline = display_name
    if date is not None:
        headline += " at " + date.strftime("%Y-%m-%d %H:%M")

    return Story(
        headline=headline,
        body_html=_text_to_html(post_text),
        byline="@" + handle,
        date=date,
        section_title="Bluesky",
        short_form=True,
    )


def _parse_bsky_datetime(value: Optional[str]) -> Optional[datetime.datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed


def _text_to_html(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "<p></p>"

    paragraphs = []
    for block in re.split(r"\n{2,}", stripped):
        escaped = escape(block).replace("\n", "<br />")
        paragraphs.append(f"<p>{escaped}</p>")
    return "".join(paragraphs)
