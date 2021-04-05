import feedparser
import bs4
from typing import List

from .util import PlacementPreference
from .storyprovider import StoryProvider
from .story import Story


class WikipediaCurrentEventsStoryProvider(StoryProvider):
    """
    A story provider that reads from today's current events on Wikipedia.
    """

    def __init__(self):
        pass

    def get_stories(self, limit: int = 10, since = None) -> List[Story]:
        """
        Get a list of current stories from Wikipedia.
        """
        feed = feedparser.parse("https://www.to-rss.xyz/wikipedia/current_events/")
        # title = feed.entries[0].title
        title = "Today's Current Events"
        content = bs4.BeautifulSoup(feed.entries[0].summary, "lxml")
        for a in content.find_all("a"):
            while a.find("li"):
                a.find("li").replace_with_children()
            while a.find("ul"):
                a.find("ul").replace_with_children()
            a.replace_with_children()

        while content.find("dl"):
            content.find("dl").name = "h3"
        return [
            Story(
                headline=title,
                body_html=str(content),
                byline="Wikipedia Current Events",
                placement_preference=PlacementPreference.BANNER,
            )
        ]
