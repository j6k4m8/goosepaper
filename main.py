from goosepaper import Goosepaper, WikipediaCurrentEventsStoryProvider, TwitterStoryProvider, LoremStoryProvider, WeatherStoryProvider

print(
    Goosepaper([
        WikipediaCurrentEventsStoryProvider(),
        WeatherStoryProvider(woe="2358820"),
        TwitterStoryProvider("reuters", limit=5),
        TwitterStoryProvider("bbcWorld", limit=5),
    ]).to_html()
)
