from goosepaper import (
    Goosepaper,
    RSSFeedStoryProvider,
    WikipediaCurrentEventsStoryProvider,
    TwitterStoryProvider,
    LoremStoryProvider,
    WeatherStoryProvider,
)

print(
    Goosepaper(
        [
            WikipediaCurrentEventsStoryProvider(),
            WeatherStoryProvider(woe="2358820"),
            RSSFeedStoryProvider("https://www.statnews.com/feed/", limit=5),
            TwitterStoryProvider("reuters", limit=5),
            TwitterStoryProvider("bbcWorld", limit=5),
        ]
    ).to_html()
)
