from goosepaper import (
    Goosepaper,
    RedditHeadlineStoryProvider,
    RSSFeedStoryProvider,
    WeatherStoryProvider,
    WikipediaCurrentEventsStoryProvider,
    # MultiTwitterStoryProvider,
    transfer_file_to_remarkable,
)

from datetime import datetime
import logging

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


transfer_file_to_remarkable(FNAME)
logging.info(f"HONK! I'm done :)")
