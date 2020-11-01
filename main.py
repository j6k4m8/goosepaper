from goosepaper import (
    Goosepaper,
    RedditHeadlineStoryProvider,
    RSSFeedStoryProvider,
    WeatherStoryProvider,
    WikipediaCurrentEventsStoryProvider,
    # MultiTwitterStoryProvider,
)

print(
    Goosepaper(
        [
            WikipediaCurrentEventsStoryProvider(),
            WeatherStoryProvider(woe="2358820"),
            RSSFeedStoryProvider("https://www.statnews.com/feed/", limit=5),
            RSSFeedStoryProvider("https://www.npr.org/feed/", limit=5),
            # MultiTwitterStoryProvider(
            #    ["reuters", "bbcWorld", "axios", "BethanyAllenEbr", "NPR"], limit_per=5
            # ),
            # Pending this issue: https://github.com/j6k4m8/goosepaper/issues/5
            RedditHeadlineStoryProvider("news"),
            RedditHeadlineStoryProvider("todayilearned"),
        ]
    ).to_html()
)
