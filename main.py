from typing import List
import feedparser

DEFAULT_FEEDS = {
    "Reuters": "http://feeds.reuters.com/reuters/topNews.rss",
    "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
}

FEEDS = [
    feedparser.parse(feed)
    for feed in [
        "https://morss.it/https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://morss.it/feeds.reuters.com/reuters/topNews.rss",
        "https://morss.it/feeds.bbci.co.uk/news/rss.xml",
    ]
]

entries = []
for feed in FEEDS:
    entries = [*entries, *feed.entries]

html_entries = []

for entry in entries:
    if "content" not in entry:
        continue
    html_entries.append(
        f"""
    <article>
        <h1>{entry['title']}</h1>
        <h4>{entry['published']}</h4>
        {entry['content'][0]['value']}
    </article>
    """
    )

print("<hr />".join(html_entries))
