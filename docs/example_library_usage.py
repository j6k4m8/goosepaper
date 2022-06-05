import logging
from datetime import datetime

from goosepaper.goosepaper import Goosepaper
from goosepaper.storyprovider.reddit import RedditHeadlineStoryProvider
from goosepaper.storyprovider.rss import RSSFeedStoryProvider
from goosepaper.storyprovider.twitter import MultiTwitterStoryProvider
from goosepaper.storyprovider.weather import OpenMeteoWeatherStoryProvider
from goosepaper.storyprovider.wikipedia import WikipediaCurrentEventsStoryProvider
from goosepaper.upload import upload


FNAME = datetime.now().strftime("%Y-%m-%d") + ".pdf"
logging.info("Honk! I will save your temporary PDF to {FNAME}.")


logging.info("Generating paper...")
Goosepaper(
    [
        WikipediaCurrentEventsStoryProvider(),
        OpenMeteoWeatherStoryProvider(lat=42.3601, lon=-71.0589, F=True),
        RSSFeedStoryProvider("https://www.npr.org/feed/", limit=5),
        RSSFeedStoryProvider("https://www.statnews.com/feed/", limit=2),
        MultiTwitterStoryProvider(["reuters", "bbcWorld", "axios", "NPR"], limit_per=5),
        RedditHeadlineStoryProvider("news"),
        RedditHeadlineStoryProvider("todayilearned"),
    ]
).to_pdf(FNAME)
logging.info("Saved to PDF, now transferring...")


upload(FNAME)
logging.info("HONK! I'm done :)")
