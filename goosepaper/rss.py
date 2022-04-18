import requests
import feedparser
from typing import List
from readability import Document
import multiprocessing
import time

from .story import Story
from .util import PlacementPreference
from .storyprovider import StoryProvider


class RSSFeedStoryProvider(StoryProvider):
    def __init__(
        self,
        title: str,
        link: str,
        rss_path: str,
        limit: int = 5,
        parallel: bool = True,
        memory: bool = False,
    ) -> None:
        self.title = title
        self.link = link
        self.limit = limit
        self.feed_url = rss_path
        self._parallel = parallel
        self.memory = memory

    def get_stories(self, limit: int = 20) -> List[Story]:
        feed = feedparser.parse(self.feed_url)
        limit = min(limit, self.limit, len(feed.entries))
        title = Story(
            headline=f"<h1>{self.title}</h1>",
            body_html=f"""<a href={self.link}>{self.link}</a><br><br>""",
        )

        if limit == 0:
            print(f"Sad honk :/ No entries found for feed {self.feed_url}...")

        if self._parallel:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                stories = pool.map(self.parallelizable_request, feed.entries[:limit])
        else:
            stories = [self.parallelizable_request(e) for e in feed.entries[:limit]]

        if self.memory:
            try:
                # Find file and make target
                with open(f"data/{self.title}.txt", "r") as f:
                    data = f.readlines()
                    f.close()

                data = [data[i].strip() for i in range(len(data))]

            except IOError:
                with open(f"data/{self.title}.txt", "w") as f:
                    f.write("")
                    f.close()

                data = []

            stories = list(filter(None, stories))

            # Check if hash of newsstory is in file
            hex_stories = [stories[i].to_hex() for i in range(len(stories))]

            i = 0
            while i < len(hex_stories):
                if hex_stories[i] in data:
                    del hex_stories[i]
                    del stories[i]
                else:
                    i = i + 1

            # Store new hashes of titles in datafile for each rss source
            with open(f"data/{self.title}.txt", "a") as f:
                for digest in hex_stories:
                    f.write(digest + "\n")
                f.close()

        if len(stories) == 0:
            emptyStory = Story(
                headline=f"<h2>No new stories from {self.title}.</h2>",
                body_html=f"""<p>You should add some new sources in your config file.</p>
                <p>This message appears as you have enabled RSS-memory. This can be disabled in your config-file.</p>
                """,
            )
            stories.insert(0, emptyStory)

        stories.insert(0, title)

        return stories

    def parallelizable_request(self, entry):
        req = requests.get(entry["link"])
        if not req.ok:
            print(f"Honk! Couldn't grab content for {self.feed_url}")
            return None

        byline = ""
        try:
            byline += entry["author"]
        except KeyError:
            pass

        try:
            byline += " - " + entry["published"]
            try:
                byline += " (Updated: " + time.asctime(entry["updated_parsed"]) + " )"
            except KeyError:
                pass
        except KeyError:
            pass



        doc = Document(req.content)
        source = entry["link"].split(".")[1]
        story = Story(
            headline=f"<h2>{doc.title()}</h2>",
            body_html=doc.summary().replace("h2", "h3").replace("h1", "h2"),# entry["summary"],
            byline=byline,
        )

        return story
