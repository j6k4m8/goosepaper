import datetime
import os

from uuid import uuid4
from typing import List
from ebooklib import epub

from .styles import Style, AutumnStyle

from goosepaper.util import PlacementPreference, StoryProvider
from goosepaper.story import Story


class Goosepaper:
    def __init__(
        self,
        story_providers: List[StoryProvider],
        title: str = None,
        subtitle: str = None,
    ):
        self.story_providers = story_providers
        self.title = title if title else "Daily Goosepaper"
        self.subtitle = (
            subtitle if subtitle else datetime.datetime.today().strftime("%B %d, %Y")
        )

    def to_html(self) -> str:
        stories = []
        for prov in self.story_providers:
            new_stories = prov.get_stories()
            for a in new_stories:
                found = False
                for b in stories:
                    if a.headline == b.headline:
                        found = True
                        break
                if not found:
                    stories.append(a)

        # Get ears:
        ears = [s for s in stories if s.placement_preference ==
                PlacementPreference.EAR]
        right_ear = ""
        left_ear = ""
        if len(ears) > 0:
            right_ear = ears[0].to_html()
        if len(ears) > 1:
            left_ear = ears[1].to_html()

        main_stories = [
            s.to_html()
            for s in stories
            if s.placement_preference
            not in [PlacementPreference.EAR, PlacementPreference.SIDEBAR]
        ]

        sidebar_stories = [
            s.to_html()
            for s in stories
            if s.placement_preference == PlacementPreference.SIDEBAR
        ]

        return f"""
            <html>
            <head>
                <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
                <meta charset="UTF-8" />
            </head>
            <body>
                <div class="header">
                    <div class="left-ear ear">{left_ear}</div>
                    <div><h1>{self.title}</h1><h4>{self.subtitle}</h4></div>
                    <div class="right-ear ear">{right_ear}</div>
                </div>
                <div class="stories row">
                    <div class="main-stories column">
                        {"<hr />".join(main_stories)}
                    </div>
                    <div class="sidebar column">
                        {"<br />".join(sidebar_stories)}
                    </div>
                </div>
            </body>
            </html>
        """

    def to_pdf(self, filename: str, style: Style = AutumnStyle) -> str:
        """
        Renders the current Goosepaper to a PDF file on disk.

        TODO: If an IO type is provided, write bytes instead.

        """
        from weasyprint import HTML, CSS

        style = style()
        html = self.to_html()
        h = HTML(string=html)
        c = CSS(string=style.get_css())
        h.write_pdf(filename, stylesheets=[c, *style.get_stylesheets()])
        return filename

    def to_epub(self, filename: str, style: Style = AutumnStyle) -> str:
        """
        Render the current Goosepaper to an epub file on disk
        """
        stories = []
        for prov in self.story_providers:
            new_stories = prov.get_stories()
            for a in new_stories:

                if not a.headline:
                    stories.append(a)
                    continue
                for b in stories:
                    if a.headline == b.headline:
                        break
                else:
                    stories.append(a)

        book = epub.EpubBook()
        title = f"{self.title} - {self.subtitle}"
        book.set_title(title)
        book.set_language('en')

        style = Style()
        css = epub.EpubItem(uid="style_default", file_name="style/default.css",
                            media_type="text/css", content=style.get_css())
        book.add_item(css)

        chapters = []
        links = []
        no_headlines = []
        for story in stories:
            if not story.headline:
                no_headlines.append(story)
        stories = [x for x in stories if x.headline]
        for story in stories:
            file = f'{uuid4().hex}.xhtml'
            title = story.headline
            chapter = epub.EpubHtml(title=title, file_name=file, lang='en')
            links.append(file)
            chapter.content = story.to_html()
            book.add_item(chapter)
            chapters.append(chapter)

        if no_headlines:
            file = f'{uuid4().hex}.xhtml'
            chapter = epub.EpubHtml(
                title="From Reddit", file_name=file, lang='en')
            links.append(file)
            chapter.content = '<br>'.join([s.to_html() for s in no_headlines])
            book.add_item(chapter)
            chapters.append(chapter)

        book.toc = chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + chapters

        print(f"Honk! Writing out epub {filename}")
        epub.write_epub(filename, book)
