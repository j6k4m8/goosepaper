import datetime
import io
import pathlib
import re
import tempfile
from html import escape
from typing import List, Optional, Type, Union
from uuid import uuid4

from goosepaper.story import Story

from .styles import Style
from .storyprovider.storyprovider import StoryProvider
from .util import PlacementPreference


def _get_style(style):
    if isinstance(style, str):
        style_obj = Style(style)
    else:
        try:
            style_obj = style()
        except Exception as err:
            raise ValueError(f"Invalid style {style}") from err
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
            try:
                new_stories = prov.get_stories()
            except Exception as err:
                print(
                    f"Sad honk :/ Failed to fetch stories from {prov.__class__.__name__}: {err}"
                )
                continue
            for story in new_stories:
                if deduplicate:
                    for existing in stories:
                        if (
                            story.headline == existing.headline
                            and story.date == existing.date
                        ):
                            break
                    else:
                        stories.append(story)
                else:
                    stories.append(story)
        return stories

    def _render_html_document(
        self,
        *,
        style: Union[str, Type[Style]] = "",
        font_size: int = 14,
        body_font: str | None = None,
        table_of_contents: bool = False,
        layout: str = "auto",
        page_profile: str = "remarkable2",
        embed_styles: bool = True,
    ) -> str:
        style_obj = _get_style(style)
        stories = self.get_stories()
        effective_columns = style_obj.resolve_column_count(layout, page_profile)

        ears = [
            story
            for story in stories
            if story.placement_preference == PlacementPreference.EAR
        ]
        right_ear = (
            ears[0].to_html(extra_classes=["ear-story"]) if len(ears) > 0 else ""
        )
        left_ear = (
            ears[1].to_html(extra_classes=["ear-story"]) if len(ears) > 1 else ""
        )

        main_story_objects = [
            story
            for story in stories
            if story.placement_preference
            not in [
                PlacementPreference.EAR,
                PlacementPreference.SIDEBAR,
                PlacementPreference.UTILITY,
            ]
        ]

        utility_story_objects = [
            story
            for story in stories
            if story.placement_preference == PlacementPreference.UTILITY
        ]

        sidebar_story_objects = [
            story
            for story in stories
            if story.placement_preference == PlacementPreference.SIDEBAR
        ]
        ordered_story_objects = (
            utility_story_objects + main_story_objects + sidebar_story_objects
        )
        story_anchor_ids = self._story_anchor_ids(ordered_story_objects)
        story_numbers = {
            id(story): index
            for index, story in enumerate(ordered_story_objects, start=1)
        }
        used_anchors = set(story_anchor_ids.values())
        utility_stories, utility_toc_entries = self._render_story_region(
            utility_story_objects,
            story_anchor_ids,
            story_numbers,
            used_anchors=used_anchors,
        )
        main_stories, main_toc_entries = self._render_story_region(
            main_story_objects,
            story_anchor_ids,
            story_numbers,
            used_anchors=used_anchors,
        )
        sidebar_stories, sidebar_toc_entries = self._render_story_region(
            sidebar_story_objects,
            story_anchor_ids,
            story_numbers,
            used_anchors=used_anchors,
        )
        toc_html = self._render_table_of_contents(
            utility_toc_entries + main_toc_entries + sidebar_toc_entries,
            enabled=table_of_contents,
            effective_columns=effective_columns,
        )
        subtitle_html = "<br />".join(
            escape(line) for line in self.subtitle.splitlines() if line.strip()
        )
        header_classes = ["header"]
        if left_ear:
            header_classes.append("has-left-ear")
        if right_ear:
            header_classes.append("has-right-ear")
        stories_classes = ["stories", f"stories--{effective_columns}col"]
        if sidebar_stories:
            stories_classes.append("has-sidebar")
        sidebar_html = ""
        if sidebar_stories:
            sidebar_html = f"""
                    <div class="sidebar">
                        <h2 class="sidebar-title">Briefs & notes</h2>
                        {''.join(sidebar_stories)}
                    </div>
            """
        utility_html = ""
        if utility_stories:
            utility_html = f"""
                    <div class="utility-strip">
                        {''.join(utility_stories)}
                    </div>
            """

        stylesheet_links = ""
        style_block = ""
        body_classes = [
            f"theme-{escape(style_obj.style_name)}",
            f"page-{escape(page_profile)}",
            f"columns-{effective_columns}",
            "has-toc" if toc_html else "no-toc",
        ]
        if embed_styles:
            stylesheet_links = "".join(
                f'<link rel="stylesheet" href="{url}">'
                for url in style_obj.get_stylesheets()
            )
            style_block = (
                "<style>"
                + style_obj.get_css(
                    font_size=font_size,
                    body_font=body_font,
                    layout=layout,
                    page_profile=page_profile,
                )
                + "</style>"
            )

        return f"""
            <html>
            <head>
                <meta
                    http-equiv="Content-type"
                    content="text/html;
                    charset=utf-8" />
                <meta charset="UTF-8" />
                {stylesheet_links}
                {style_block}
            </head>
            <body class="{' '.join(body_classes)}">
                <div class="{' '.join(header_classes)}">
                    <div class="left-ear ear">{left_ear}</div>
                    <div class="masthead">
                        <h1>{escape(self.title)}</h1>
                        <p class="edition-line">{subtitle_html}</p>
                    </div>
                    <div class="right-ear ear">{right_ear}</div>
                </div>
                {utility_html}
                {toc_html}
                <div class="{' '.join(stories_classes)}">
                    <div class="main-stories">
                        {''.join(main_stories)}
                    </div>
                    {sidebar_html}
                </div>
            </body>
            </html>
        """

    def to_html(
        self,
        style: Union[str, Type[Style]] = "",
        font_size: int = 14,
        body_font: str | None = None,
        table_of_contents: bool = False,
        layout: str = "auto",
        page_profile: str = "remarkable2",
    ) -> str:
        """
        Produce an HTML version of the Goosepaper.

        Returns:
            str: An HTML version of the paper

        """
        return self._render_html_document(
            style=style,
            font_size=font_size,
            body_font=body_font,
            table_of_contents=table_of_contents,
            layout=layout,
            page_profile=page_profile,
            embed_styles=True,
        )

    def to_pdf(
        self,
        filename: Union[str, io.BytesIO],
        style: Union[str] = "",
        font_size: int = 14,
        body_font: str | None = None,
        table_of_contents: bool = False,
        layout: str = "auto",
        page_profile: str = "remarkable2",
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
        from weasyprint import CSS, HTML
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()
        style_obj = _get_style(style)
        html = self._render_html_document(
            style=style,
            font_size=font_size,
            body_font=body_font,
            table_of_contents=table_of_contents,
            layout=layout,
            page_profile=page_profile,
            embed_styles=False,
        )
        base_url = str(pathlib.Path.cwd())
        h = HTML(string=html, base_url=base_url)
        c = CSS(
            string=style_obj.get_css(
                font_size=font_size,
                body_font=body_font,
                layout=layout,
                page_profile=page_profile,
            ),
            font_config=font_config,
            base_url=base_url,
        )
        if isinstance(filename, str):
            h.write_pdf(
                filename,
                stylesheets=[c, *style_obj.get_stylesheets()],
                font_config=font_config,
            )
            return filename
        if isinstance(filename, io.BytesIO):
            tf = tempfile.NamedTemporaryFile(suffix=".pdf")
            h.write_pdf(
                tf,
                stylesheets=[c, *style_obj.get_stylesheets()],
            )
            tf.seek(0)
            filename.write(tf.read())
            return None
        raise ValueError(f"Invalid filename {filename}")

    def _render_story_region(
        self,
        stories: List[Story],
        story_anchor_ids: dict[int, str],
        story_numbers: dict[int, int],
        *,
        used_anchors: set[str],
    ) -> tuple[list[str], list[tuple[str, str]]]:
        rendered: list[str] = []
        toc_entries: list[tuple[str, str]] = []

        for section_title, run_stories in self._story_runs(stories):
            if section_title:
                section_anchor = self._unique_anchor(
                    f"section-{self._slugify(section_title)}",
                    used_anchors,
                )
                rendered.append(
                    f"""
                    <div id="{escape(section_anchor)}" class="story-section-heading">
                        <h2 class="story-section-title">{escape(section_title)}</h2>
                    </div>
                    """
                )
                if any(story.include_in_toc for story in run_stories):
                    toc_entries.append((section_title, section_anchor))

            for story in run_stories:
                rendered.append(
                    story.to_html(anchor_id=story_anchor_ids[id(story)])
                )
                if section_title or not story.include_in_toc:
                    continue
                headline = story.headline or f"Untitled story {story_numbers[id(story)]}"
                toc_entries.append((headline, story_anchor_ids[id(story)]))

        return rendered, toc_entries

    def _story_runs(
        self, stories: List[Story]
    ) -> list[tuple[Optional[str], List[Story]]]:
        runs: list[tuple[Optional[str], List[Story]]] = []
        current_title: Optional[str] = None
        current_stories: list[Story] = []

        for story in stories:
            section_title = (story.section_title or "").strip() or None
            if current_stories and section_title and section_title == current_title:
                current_stories.append(story)
                continue
            if current_stories:
                runs.append((current_title, current_stories))
            current_title = section_title
            current_stories = [story]

        if current_stories:
            runs.append((current_title, current_stories))

        return runs

    def _story_anchor_ids(self, stories: List[Story]) -> dict[int, str]:
        anchors: dict[int, str] = {}
        used = set()
        for index, story in enumerate(stories, start=1):
            stem = self._slugify(story.headline or f"story-{index}")
            anchor = f"story-{index}-{stem}"
            while anchor in used:
                anchor = f"{anchor}-x"
            used.add(anchor)
            anchors[id(story)] = anchor
        return anchors

    def _render_table_of_contents(
        self,
        toc_entries: List[tuple[str, str]],
        *,
        enabled: bool,
        effective_columns: int,
    ) -> str:
        if not enabled or not toc_entries:
            return ""

        items = []
        for headline, anchor_id in toc_entries:
            items.append(
                '<div class="table-of-contents__entry">'
                f'<a class="table-of-contents__link" href="#{escape(anchor_id)}">'
                f'<span class="table-of-contents__title">{escape(headline)}</span>'
                "</a>"
                "</div>"
            )
        toc_columns = 1 if effective_columns == 1 else 2
        return f"""
            <nav class="table-of-contents table-of-contents--{toc_columns}col" aria-label="Contents">
                <div class="table-of-contents__label">Contents</div>
                <div class="table-of-contents__entries">
                    {''.join(items)}
                </div>
            </nav>
        """

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return slug or "story"

    @staticmethod
    def _unique_anchor(base: str, used: set[str]) -> str:
        anchor = base
        suffix = 2
        while anchor in used:
            anchor = f"{base}-{suffix}"
            suffix += 1
        used.add(anchor)
        return anchor

    def to_epub(
        self,
        filename: Union[str, io.BytesIO],
        style: Union[str, Type[Style]] = "",
        font_size: int = 14,
        body_font: str | None = None,
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
        for story in self.get_stories():
            if not story.headline:
                stories.append(story)
                continue
            for existing in stories:
                if story.headline == existing.headline:
                    break
            else:
                stories.append(story)

        book = epub.EpubBook()
        title = f"{self.title} - {self.subtitle}"
        book.set_title(title)
        book.set_language("en")

        css = epub.EpubItem(
            uid="style_default",
            file_name="style/default.css",
            media_type="text/css",
            content=style_obj.get_epub_css(font_size=font_size, body_font=body_font),
        )
        book.add_item(css)

        chapters = []
        no_headlines = []
        for story in stories:
            if not story.headline:
                no_headlines.append(story)
        stories = [story for story in stories if story.headline]
        for story in stories:
            file_name = f"{uuid4().hex}.xhtml"
            chapter = epub.EpubHtml(
                title=story.headline,
                file_name=file_name,
                lang="en",
            )
            chapter.content = story.to_html()
            book.add_item(chapter)
            chapters.append(chapter)

        if no_headlines:
            file_name = f"{uuid4().hex}.xhtml"
            chapter = epub.EpubHtml(
                title="From Reddit",
                file_name=file_name,
                lang="en",
            )
            chapter.content = "<br>".join([story.to_html() for story in no_headlines])
            book.add_item(chapter)
            chapters.append(chapter)

        book.toc = chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav"] + chapters

        if isinstance(filename, str):
            epub.write_epub(filename, book)
            return filename
        if isinstance(filename, io.BytesIO):
            tf = tempfile.NamedTemporaryFile(suffix=".epub")
            epub.write_epub(tf, book)
            tf.seek(0)
            filename.write(tf.read())
            return None
        raise ValueError(f"Invalid filename {filename}")
