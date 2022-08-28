import pathlib
from typing import List, Optional, Type, Union
import datetime
import io
import tempfile
from uuid import uuid4

from goosepaper.story import Story

from .styles import Style
from .util import PlacementPreference
from .storyprovider.storyprovider import StoryProvider


def _get_style(style):
    if isinstance(style, str):
        style_obj = Style(style)
    else:
        try:
            style_obj = style()
        except Exception as e:
            raise ValueError(f"Invalid style {style}") from e
    return style_obj


class Goosepaper:
    """
    A high-level class that manages the creation and styling of a goosepaper
    periodical delivery.

    """

    def __init__(
        self,
        story_providers: List[StoryProvider],
        title: str = None,
        subtitle: str = None,
    ):
        """
        Create a new Goosepaper.

        Arguments:
            story_providers: A list of StoryProvider objects to render
            title: The title of the goosepaper
            subtitle: The subtitle of the goosepaper

        """
        self.story_providers = story_providers
        self.title = title if title else "Daily Goosepaper"
        self.subtitle = subtitle + "\n" if subtitle else ""
        self.subtitle += datetime.datetime.today().strftime("%B %d, %Y %H:%M")

    def get_stories(self, deduplicate: bool = False) -> List[Story]:
        """
        Retrieve the complete list of stories to render in this Goosepaper.

        Arguments:
            deduplicate: Whether to remove duplicate stories. Default: False

        Returns:
            List[Story]

        """
        stories: List[Story] = []
        for prov in self.story_providers:
            new_stories = prov.get_stories()
            for a in new_stories:
                if deduplicate:
                    for b in stories:
                        if a.headline == b.headline and a.date == b.date:
                            break
                    else:
                        stories.append(a)
                else:
                    stories.append(a)
        return stories

    def to_html(self) -> str:
        """
        Produce an HTML version of the Goosepaper.

        Arguments:
            None

        Returns:
            str: An HTML version of the paper

        """
        stories = self.get_stories()

        # Get ears:
        ears = [
            s
            for s in stories
            # TODO: Which to prioritize?
            if s.placement_preference == PlacementPreference.EAR
        ]
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
                <meta
                    http-equiv="Content-type"
                    content="text/html;
                    charset=utf-8" />
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

    def to_pdf(
        self,
        filename: Union[str, io.BytesIO],
        style: Union[str] = "",
        font_size: int = 14,
    ) -> Optional[str]:
        """
        Renders the current Goosepaper to a PDF file on disk.

        Arguments:
            filename: The filename to save the PDF to. If this is an io.BytesIO
                object, the PDF will be written to the object instead and this
                function will return None.
            style: The style to use for the paper. Default: FifthAvenueStyle
            font_size: The font size to use for the paper. Default: 14

        Returns:
            str: The filename of the PDF file. If `filename` is an IO object,
                then this will return None.

        """
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()
        style_obj = _get_style(style)
        html = self.to_html()
        h = HTML(string=html)
        base_url = str(pathlib.Path.cwd())
        c = CSS(
            string=style_obj.get_css(font_size),
            font_config=font_config,
            base_url=base_url,
        )
        # Check if the file is a filepath (str):
        if isinstance(filename, str):
            h.write_pdf(
                filename,
                stylesheets=[c, *style_obj.get_stylesheets()],
                font_config=font_config,
            )
            return filename
        elif isinstance(filename, io.BytesIO):
            # Create a tempfile to save the PDF to:
            tf = tempfile.NamedTemporaryFile(suffix=".pdf")
            h.write_pdf(
                tf,
                stylesheets=[c, *style_obj.get_stylesheets()],
            )
            tf.seek(0)
            filename.write(tf.read())
            return None
        else:
            raise ValueError(f"Invalid filename {filename}")

    def to_epub(
        self,
        filename: Union[str, io.BytesIO],
        style: Union[str, Type[Style]] = "",
        font_size: int = 14,
    ) -> Optional[str]:
        """
        Render the current Goosepaper to an epub file on disk.

        Arguments:
            filename: The filename to save the epub to. If `filename` is an
                IO object, then this will return None and the epub will be
                written to that object.
            style: The style to use for the paper. Default: FifthAvenueStyle
            font_size: The font size to use for the paper. Default: 14

        """
        from ebooklib import epub

        style_obj = _get_style(style)

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
        book.set_language("en")

        css = epub.EpubItem(
            uid="style_default",
            file_name="style/default.css",
            media_type="text/css",
            content=style_obj.get_css(font_size),
        )
        book.add_item(css)

        chapters = []
        links = []
        no_headlines = []
        for story in stories:
            if not story.headline:
                no_headlines.append(story)
        stories = [x for x in stories if x.headline]
        for story in stories:
            file = f"{uuid4().hex}.xhtml"
            title = story.headline
            chapter = epub.EpubHtml(title=title, file_name=file, lang="en")
            links.append(file)
            chapter.content = story.to_html()
            book.add_item(chapter)
            chapters.append(chapter)

        if no_headlines:
            file = f"{uuid4().hex}.xhtml"
            chapter = epub.EpubHtml(
                title="From Reddit",
                file_name=file,
                lang="en",
            )
            links.append(file)
            chapter.content = "<br>".join([s.to_html() for s in no_headlines])
            book.add_item(chapter)
            chapters.append(chapter)

        book.toc = chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav"] + chapters

        if isinstance(filename, str):
            epub.write_epub(filename, book)
            return filename
        elif isinstance(filename, io.BytesIO):
            # Create a tempfile buffer:
            tf = tempfile.NamedTemporaryFile(suffix=".epub")
            epub.write_epub(tf, book)
            tf.seek(0)
            filename.write(tf.read())
            return None
