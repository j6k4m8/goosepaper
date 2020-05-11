from typing import List
import pandas as pd
import datetime
import abc
import enum

import twint

import bs4
import feedparser
import requests

from .styles import Styles


def htmlize(text: str) -> str:
    """
    Generate HTML text from a text string, correctly formatting paragraphs etc.
    """
    # TODO:
    #   * Escaping
    #   * Paragraph delims
    #   * Remove illegal elements
    if isinstance(text, list):
        return "".join([f"<p>{line}</p>" for line in text])
    return f"<p>{text}</p>"


class PlacementPreference(enum.Enum):
    NONE = 0
    FULLPAGE = 1
    SIDEBAR = 2
    EAR = 3
    FOLIO = 4
    BANNER = 5


class StoryPriority(enum.Enum):
    DEFAULT = 0
    LOW = 1
    HEADLINE = 5
    BANNER = 9


class Story:
    def __init__(
        self,
        headline: str,
        body_html: str = None,
        body_text: str = None,
        byline: str = None,
        date: datetime.datetime = None,
        priority: int = StoryPriority.DEFAULT,
        placement_preference: PlacementPreference = PlacementPreference.NONE,
    ) -> None:
        """
        Create a new Story with headline and body text.
        """
        self.headline = headline
        self.priority = priority
        self.byline = byline
        self.body_html = body_html if body_html else htmlize(body_text)
        self.placement_preference = placement_preference

    def to_html(self):
        byline_h4 = f"<h4 class='byline'>{self.byline}</h4>" if self.byline else ""
        priority_class = {
            StoryPriority.DEFAULT: "",
            StoryPriority.LOW: "priority-low",
            StoryPriority.BANNER: "priority-banner",
        }[self.priority]
        headline = (
            f"<h1 class='{priority_class}'>{self.headline}</h1>"
            if self.headline
            else ""
        )
        return f"""
        <article>
            {headline}
            {byline_h4}
            {self.body_html}
        </article>
        """


class StoryProvider(abc.ABC):
    """
    An abstract class for a class that provides stories to be rendered.
    """

    def get_stories(self, limit: int = 5):
        """
        Get a list of stories from this Provider.
        """
        ...


class WikipediaCurrentEventsStoryProvider(StoryProvider):
    """
    A story provider that reads from today's current events on Wikipedia.
    """

    def __init__(self):
        pass

    def get_stories(self, limit: int = 10) -> List[Story]:
        """
        Get a list of current stories from Wikipedia.
        """
        feed = feedparser.parse("https://www.to-rss.xyz/wikipedia/current_events/")
        # title = feed.entries[0].title
        title = "Today's Current Events (Wiki)"
        content = bs4.BeautifulSoup(feed.entries[0].summary)
        for a in content.find_all("a"):
            while a.find("li"):
                a.find("li").replace_with_children()
            while a.find("ul"):
                a.find("ul").replace_with_children()
            a.replace_with_children()

        # while content.find("a"):
        #     content.find("a").replace_with_children()
        # while content.find("dt"):
        #     content.find("dt").name = "h3"
        # content.find("dt").replace_with_children()
        # while content.find("ul"):
        #     content.find("ul").replace_with_children()
        while content.find("dl"):
            content.find("dl").name = "h3"
        # for el in content.find_all("li"):
        #     content.find("ul").replace_with_children()
        return [
            Story(
                headline=title,
                body_html=str(content),
                byline="Wikipedia Current Events",
                placement_preference=PlacementPreference.SIDEBAR,
            )
        ]


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
        priority_mode: TwitterStoryProviderPriorityMode = TwitterStoryProviderPriorityMode.DEFAULT,
    ) -> None:
        """
        Create a new TwitterStoryProvider that reads from a username.

        Prioritizes stories based upon the TwitterStoryProviderPriorityMode.
        """
        self.username = username
        self.limit = limit
        self.priority_mode = priority_mode

    def get_stories(self, limit: int = 10) -> List[Story]:
        """
        Get a list of stories.

        Here, the headline is the @username, and the body text is the tweet.
        """

        c = twint.Config()
        c.Pandas = True
        c.Username = self.username
        c.Limit = min(self.limit, limit)
        c.Hide_output = True

        twint.run.Search(c)
        df = twint.storage.panda.Tweets_df
        return [
            Story(
                headline=None,
                body_text=row.tweet,
                byline=f"@{self.username} on Twitter at {pd.to_datetime(row.date).strftime('%I:%M %p')}",
            )
            for i, row in list(df.iterrows())[: min(self.limit, limit)]
        ]


class LoremStoryProvider(StoryProvider):
    def __init__(self):
        self.text = [
            "Lorem ipsum! dolor sit amet, consectetur adipiscing elit. Duis eget velit sem. In elementum eget lorem non luctus. Vivamus tempus justo in pulvinar ultrices. Aliquam ac maximus leo. Quisque ipsum sapien, vestibulum viverra tempus ac, vestibulum quis justo. Nullam ut purus varius, bibendum metus ac, viverra enim. Phasellus sodales ullamcorper sapien pretium tristique. Duis dapibus felis quis tincidunt ultrices. Etiam purus sapien, tincidunt ac turpis vel, eleifend placerat enim. In sed mauris justo. Suspendisse ac tincidunt nunc. Nullam luctus porta pretium. Donec porttitor, nulla ut finibus pretium, augue turpis posuere ante, ac congue nunc nulla eu nisl. Phasellus imperdiet vel augue id gravida.",
            "Morbi mattis egestas quam, in tempus elit efficitur sagittis. Sed in maximus lorem. Aliquam erat volutpat. Phasellus mattis varius velit, vitae varius justo. Sed imperdiet eget dolor non consequat. Cras non felis neque. Nam eget arcu sapien. Morbi ultrices tristique cursus. Sed tempor ex lorem, vel ultrices sem placerat non. Nullam tortor arcu, imperdiet id lobortis a, commodo nec mi. Duis rhoncus in est sit amet tristique. Mauris condimentum nisl a erat tristique, id dictum risus euismod. Phasellus at sapien ante. Morbi facilisis tortor id leo porta, condimentum mollis dolor suscipit.",
            "Phasellus ut nibh vitae turpis congue venenatis. Morbi mollis justo dolor, ac finibus erat suscipit vitae. Donec libero erat, luctus quis sapien vel, sagittis dapibus est. Ut non quam et nisl hendrerit sodales. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Integer sodales ut augue a lacinia. Phasellus mattis sapien eget nibh auctor porttitor. Sed feugiat consectetur risus, a tempus ipsum scelerisque eu. Maecenas suscipit erat quis neque vulputate, ornare vehicula tellus lobortis. Duis tempor elit scelerisque ex tincidunt imperdiet. Curabitur dictum condimentum turpis, vitae ultrices ante sodales a. Praesent eu erat nec odio placerat placerat. Sed et dolor augue.",
            "Curabitur consectetur, nisi eget consequat ultrices, erat ante tincidunt ipsum, eget varius mauris turpis ac enim. Vivamus rutrum condimentum metus ut egestas. Nulla consectetur tincidunt laoreet. Vivamus tortor sem, imperdiet sodales facilisis quis, elementum nec erat. Curabitur imperdiet, nulla vel mattis gravida, risus eros sollicitudin magna, nec feugiat mauris mauris eu lorem. In hac habitasse platea dictumst. Sed tincidunt facilisis sem, non commodo metus volutpat nec. Fusce nulla mauris, vulputate sit amet magna id, blandit ornare leo. Nam vel faucibus ipsum, ac congue dolor.",
            "Vivamus pretium purus vel libero finibus blandit. Donec vitae nisl sollicitudin, consectetur nunc ac, volutpat libero. Maecenas ac leo ut velit viverra aliquet non id turpis. Morbi ut euismod erat. Vestibulum congue sed erat nec dapibus. Donec semper consectetur vestibulum. Praesent egestas dolor a ante sodales maximus. Suspendisse a odio vitae odio sagittis sollicitudin in quis massa. Praesent at convallis nulla. Mauris a nisl tincidunt, iaculis lacus eget, lobortis sapien. Nullam condimentum neque quis nisi consequat, eget accumsan tellus fermentum. Quisque dictum, nunc et pretium accumsan, lacus eros pharetra odio, ac euismod orci lorem sed turpis. ",
        ]

    def get_stories(self, limit: int = 5) -> List[Story]:
        return [
            Story(headline="Lorem Ipsum Dolor Sit Amet", body_text=self.text)
            for _ in range(limit)
        ]


class WeatherStoryProvider(StoryProvider):
    def __init__(self, woe: str = "2358820"):
        self.woe = woe

    def get_stories(self, limit: int = 1) -> List[Story]:
        weather = requests.get(
            f"https://www.metaweather.com/api/location/{self.woe}/"
        ).json()["consolidated_weather"][0]
        headline = f"{int((weather['the_temp'] * 9/5) + 32)}ºF with {weather['weather_state_name']}"
        body_html = f"""
        <img
            src="https://www.metaweather.com/static/img/weather/png/64/{weather['weather_state_abbr']}.png"
            width="42" />
        {int((weather['min_temp'] * 9/5) + 32)} – {int((weather['max_temp'] * 9/5) + 32)}ºF, Winds {weather['wind_direction_compass']}
        """

        return [
            Story(
                headline=headline,
                body_html=body_html,
                placement_preference=PlacementPreference.EAR,
            )
        ]


class RSSFeedStoryProvider(StoryProvider):
    def __init__(self, rss_path: str, limit: int = 5) -> None:
        self.limit = limit
        self.feed_url = rss_path

    def get_stories(self, limit: int = 5) -> List[Story]:
        limit = min(self.limit, limit)
        feed = feedparser.parse(self.feed_url)
        stories = []
        for entry in feed.entries[:limit]:
            html = entry.content[0]["value"]
            if len(entry.media_content):
                src = entry.media_content[0]["url"]
                html = f"<figure><img class='hero-img' src='{src}' /></figure>'" + html
            stories.append(Story(entry.title, body_html=html))
        return stories


class Goosepaper:
    def __init__(
        self,
        story_providers: List[StoryProvider],
        title: str = None,
        subtitle: str = None,
        style: str = Styles.Autumn,
    ):
        self.story_providers = story_providers
        self.title = title if title else "Daily Goosepaper"
        self.subtitle = (
            subtitle if subtitle else datetime.datetime.today().strftime("%B %d, %Y")
        )

    def to_html(self) -> str:
        style = Styles.Autumn

        stories = []
        for prov in self.story_providers:
            stories.extend(prov.get_stories())

        # Get ears:
        ears = [s for s in stories if s.placement_preference == PlacementPreference.EAR]
        right_ear = ""
        left_ear = ""
        if len(ears) > 0:
            right_ear = ears[0].to_html()
        if len(ears) > 1:
            left_ear = ears[1].to_html()
        stories = [
            s for s in stories if s.placement_preference != PlacementPreference.EAR
        ]

        stories = [story.to_html() for story in stories]

        return (
            "<html><head><style>"
            + style
            + "</style></head><body>"
            + "<div class='header'>"
            + f"<div class='left-ear ear'>{left_ear}</div><div><h1>{self.title}</h1><h4>{self.subtitle}</h4></div><div class='right-ear ear'>{right_ear}</div>"
            + "</div><div class='stories'>"
            + "<hr />".join(stories)
            + "</div></body></html>"
        )
