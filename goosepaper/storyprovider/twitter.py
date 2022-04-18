import datetime
import enum
import twint
from typing import List

import pandas as pd

from ..util import PlacementPreference, clean_text
from .storyprovider import StoryProvider
from ..story import Story


class TwitterStoryProviderPriorityMode(enum.Enum):
    DEFAULT = 0
    RECENT = 1
    TOP = 2
    RATIO = 3


class TwitterStoryProvider(StoryProvider):
    def __init__(
        self,
        username: str,
        limit: int = 5,
        since_days_ago: int = None,
        priority_mode: TwitterStoryProviderPriorityMode = TwitterStoryProviderPriorityMode.DEFAULT,
    ) -> None:
        """
        Create a new TwitterStoryProvider that reads from a username.

        Prioritizes stories based upon the TwitterStoryProviderPriorityMode.
        """
        self.username = username
        self.limit = limit
        self.priority_mode = priority_mode
        self._since = (
            datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
            if since_days_ago
            else None
        )

    def get_stories(self, limit: int = 10, **kwargs) -> List[Story]:
        """
        Get a list of stories.

        Here, the headline is the @username, and the body text is the tweet.
        """

        c = twint.Config()
        c.Pandas = True
        c.Search = f"from:{self.username}"
        c.Limit = min(self.limit, limit)
        c.Hide_output = True

        twint.run.Search(c)
        df = twint.storage.panda.Tweets_df  # type: ignore
        stories = []
        for _, row in list(df.iterrows()):
            date = pd.to_datetime(row.date)
            if self._since is not None and date < self._since:
                continue
            stories.append(
                Story(
                    headline=None,
                    body_text=clean_text(row.tweet),
                    byline=f"@{self.username} on Twitter at {date.strftime('%I:%M %p')}",
                    date=date,
                    placement_preference=PlacementPreference.SIDEBAR,
                )
            )
            if len(stories) >= limit:
                break
        return stories


class MultiTwitterStoryProvider(StoryProvider):
    def __init__(
        self,
        usernames: List[str],
        limit_per: int = 5,
        since_days_ago: int = None,
        priority_mode: TwitterStoryProviderPriorityMode = TwitterStoryProviderPriorityMode.DEFAULT,
    ) -> None:
        """
        Create a new story provider that reads tweets from several users.

        Arguments:
            usernames (List[str]): A list of twitter usernames
            limit_per (int: 5): A maximum number of tweets to fetch from each
                user in `usernames`
            priority_mode (TwitterStoryProviderPriorityMode): Which priority
                technique to use. Not currently implemented.

        """
        self.usernames = usernames
        self.limit_per = limit_per
        self.priority_mode = priority_mode
        self._since_days_ago = since_days_ago

    def get_stories(self, limit: int = 42, **kwargs) -> List[Story]:
        """
        Get a list of tweets where each tweet is a story.

        Arguments:
            limit (int: 15): The maximum number of tweets to fetch

        Returns:
            List[Story]: A list of tweets

        """
        stories = []
        for username in self.usernames:
            stories.extend(
                TwitterStoryProvider(
                    username, self.limit_per, self._since_days_ago, self.priority_mode
                ).get_stories(limit=self.limit_per)
            )
        stories = sorted(stories, key=lambda story: story.date)
        return stories[:limit]
