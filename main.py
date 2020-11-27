import logging
from datetime import datetime

from goosepaper.goosepaper import Goosepaper
from goosepaper.reddit import RedditHeadlineStoryProvider
from goosepaper.rss import RSSFeedStoryProvider
from goosepaper.twitter import TwitterStoryProvider
from goosepaper.weather import WeatherStoryProvider
from goosepaper.wikipedia import WikipediaCurrentEventsStoryProvider
from goosepaper.upload import upload


FNAME = datetime.now().strftime("%Y-%m-%d") + ".pdf"
logging.info(f"Honk! I will save your temporary PDF to {FNAME}.")


logging.info(f"Generating paper...")
Goosepaper(
    [
        WikipediaCurrentEventsStoryProvider(),
        WeatherStoryProvider(woe="2358820", F=False),
        RSSFeedStoryProvider("https://www.npr.org/feed/", limit=5),
        RSSFeedStoryProvider("https://www.statnews.com/feed/", limit=2),
        # MultiTwitterStoryProvider(
        # Pending this issue: https://github.com/j6k4m8/goosepaper/issues/5
        #    ["reuters", "bbcWorld", "axios", "BethanyAllenEbr", "NPR"], limit_per=5
        # ),
        RedditHeadlineStoryProvider("news"),
        RedditHeadlineStoryProvider("todayilearned"),
    ]
).to_pdf(FNAME)
logging.info(f"Saved to PDF, now transferring...")


#upload(FNAME)
logging.info(f"HONK! I'm done :)")
