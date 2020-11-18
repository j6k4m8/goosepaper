import requests
import feedparser
import bs4
from typing import List

from goosepaper.util import (
    StoryProvider, 
    PlacementPreference,
    clean_html )
from goosepaper.story import Story

class RSSFeedStoryProvider(StoryProvider):
    def __init__(self, rss_path: str, limit: int = 5) -> None:
        self.limit = limit
        self.feed_url = rss_path
    
    def parse_npr(self, content):
        story_text = content.find('div', {'id': 'storytext'})
        for item in story_text.findAll('div', {'class': 'caption'}):
            item.decompose()
        for item in story_text.findAll('span', {'class': 'credit'}):
            item.decompose()
        for item in story_text.findAll('div', {'class': 'enlarge-options'}):
            item.decompose()
        for item in story_text.findAll('div', {'class': 'credit-option'}):
            item.decompose()
        for item in story_text.findAll('div', {'class': 'image'}):
            item.decompose()
        for item in story_text.findAll('div', {'class': 'img'}):
            item.decompose()
        for item in story_text.findAll('div', {'class': 'video'}):
            item.decompose()
        for item in story_text.findAll('em'):
            item.decompose()
        return story_text
    
    def parse_nyt(self, content, limit):
        story_text = content.find('article')
        stories = []
        idx = 0
        for item in story_text.findAll('div', {'class': "live-blog-post"}):   
            html = self.decompose(item)
            
            # headline = html.find('css-608m5d')
            # headline.decompose()

            title_div = item.find('div', {'class': 'live-blog-post-headline'})
            title = str(title_div.find('a').contents[0])
            title_div.decompose()

            stories.append(Story(title, body_html=str(html)))
            idx += 1
            if idx >= limit:
                break
        return stories
    
    def decompose(self, content):
        to_remove = ['script', 'img', 'figcaption', 'aside', 'form', 'header', 'button']
        for remove in to_remove:
            for item in content.findAll(remove):
                item.decompose()
        return content

    def get_stories(self, limit: int = 5) -> List[Story]:
        feed = feedparser.parse(self.feed_url)
        limit = min(self.limit, len(feed.entries))
        stories = []
        # import ipdb; ipdb.set_trace()
        for entry in feed.entries[:limit]:
            # import ipdb; ipdb.set_trace()
            if "link" in entry.keys():
                print(entry['link'])
                req = requests.get(entry['link'])
                if not req.ok:
                    print("Honk! Couldnt grab content!")
                    continue
                
                soup = bs4.BeautifulSoup(req.content, "html.parser")
                content = self.decompose(soup)

                if 'npr.org' in entry['link']:
                    print("Honk! Found an NPR news story!")
                    content = self.parse_npr(content)
                elif 'nytimes.com' in entry['link']:
                    print("Honk! Found an NYT story!")
                    new_stories = self.parse_nyt(content, limit)
                    stories.extend(new_stories)
                    return stories
                else:
                    content = soup.find('section')
                content = str(content)
                html = clean_html(content)
                stories.append(Story(entry.title, body_html=html))
            # if "content" in entry:
            #     html = entry.content[0]["value"]
            # elif "summary_detail" in entry:
            #     html = entry.summary_detail["value"]
            # else:
            #     html = entry.summary
            # html = clean_html(html)
            # try:
            #     if len(entry.media_content):
            #         src = entry.media_content[0]["url"]
            #         html = (
            #             f"<figure><img class='hero-img' src='{src}' /></figure>'" + html
            #         )
            # except Exception:
            #     pass

                
        return stories