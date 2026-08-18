import base64
import datetime
import io
import pathlib
import re
import tempfile
from html import escape
from typing import List, Optional, Type, Union
from uuid import uuid4

import bs4
import requests

from goosepaper.story import Story

from .storyprovider.imageutil import reencode_image_as_data_uri
from .storyprovider.storyprovider import StoryProvider
from .styles import PageProfile, Style
from .util import PlacementPreference
from .version import __version__

_IMAGE_FETCH_TIMEOUT = 20
# Images are sized off the actual page geometry (see _image_max_dimension) rather than a single
# guessed constant - this DPI is the only remaining guess, chosen as a reasonable target for
# both e-ink tablets (a reMarkable 2 is ~226 DPI) and printed/on-screen PDF profiles alike.
_IMAGE_TARGET_DPI = 200
_IMAGE_MIN_DIMENSION = 400
# Used only if a page_profile's size/margins can't be parsed for some reason - matches the flat
# constant every story provider used before this was made layout-aware.
_IMAGE_DIMENSION_FALLBACK = 1200


def _get_style(style):
    if isinstance(style, str):
        style_obj = Style(style)
    else:
        try:
            style_obj = style()
        except Exception as err:
            raise ValueError(f"Invalid style {style}") from err
    return style_obj


def _parse_length_inches(value: str) -> float:
    """Parses a PageProfile length ("6.18in", "9mm") into inches - the only two units any
    bundled page_profile currently uses (see styles.py's _PAGE_PROFILES)."""
    value = value.strip()
    if value.endswith("mm"):
        return float(value[:-2]) / 25.4
    if value.endswith("in"):
        return float(value[:-2])
    raise ValueError(f"Unsupported page_profile length unit: {value!r}")


def _image_max_dimension(profile: PageProfile, effective_columns: int) -> int:
    """Derives a sensible embedded-image pixel cap from the actual page geometry: an image wider
    than what a single rendered column will ever display is pure waste, not extra quality - the
    same reasoning every story provider's old hardcoded 1200px constant used, but computed per
    page_profile/layout instead of guessed once for all six of them (a remarkable2 column and a
    letter column are not remotely the same physical width).
    """
    try:
        width_str, _height_str = profile.size.split()
        content_width_in = (
            _parse_length_inches(width_str)
            - _parse_length_inches(profile.margin_left)
            - _parse_length_inches(profile.margin_right)
        )
        column_width_in = content_width_in / max(1, effective_columns)
        return max(_IMAGE_MIN_DIMENSION, round(column_width_in * _IMAGE_TARGET_DPI))
    except (ValueError, IndexError):
        return _IMAGE_DIMENSION_FALLBACK


def _inline_story_images(body_html: str, max_dimension: int) -> str:
    """Finds every `<img>` in body_html - a remote `http(s)://` URL or an already-inlined `data:`
    URI - and replaces it with a size-capped, format-normalized `data:` JPEG via
    `imageutil.reencode_image_as_data_uri`. An image that fails to fetch or decode is removed
    from the story rather than aborting the whole story - leaving its original `http(s)://` src
    in place instead would mean WeasyPrint's own image loader tries (and fails) to fetch the same
    dead URL a second time at render time, logging the same failure twice.

    This runs once per render, here, rather than per-provider: it applies uniformly to every
    story regardless of source, and it can size images off the actual page_profile/layout being
    rendered, which no individual story provider has any visibility into.
    """
    if not body_html:
        return body_html

    soup = bs4.BeautifulSoup(body_html, "lxml")
    container = soup.body or soup
    changed = False
    for node in container.find_all("img"):
        src = node.get("src")
        if not src:
            continue
        try:
            if src.startswith(("http://", "https://")):
                response = requests.get(
                    src,
                    headers={"User-Agent": f"goosepaper/{__version__}"},
                    timeout=_IMAGE_FETCH_TIMEOUT,
                )
                response.raise_for_status()
                raw_bytes = response.content
            elif src.startswith("data:") and ";base64," in src:
                # An already-inlined image (e.g. from a second render pass) - decoded back to
                # bytes here since body_html only carries text, not bytes, between provider and
                # render step.
                raw_bytes = base64.b64decode(src.split(";base64,", 1)[1])
            else:
                continue
            node["src"] = reencode_image_as_data_uri(raw_bytes, max_dimension)
            changed = True
        except Exception as err:
            print(f"Sad honk :/ Failed to inline image {src[:80]!r}: {err}")
            node.decompose()
            changed = True

    if not changed:
        return body_html

    # A body_html fragment that starts with a bare <style> tag (e.g. comic.py's CSS block,
    # prepended before its <div>) isn't valid at the top of an HTML <body> - lxml silently
    # relocates it into an implied <head>, separate from `container`. Re-serializing only
    # `container.decode_contents()` would then drop that CSS outright. Prepending the head's
    # own content restores it, since decode_contents() otherwise plain-strips it.
    head_content = soup.head.decode_contents() if soup.head else ""
    return head_content + container.decode_contents()


def _inline_all_story_images(stories: List[Story], max_dimension: int) -> None:
    """Runs _inline_story_images() over every story in place, isolating one story's failure
    from the rest - shared by both to_html()/to_pdf() (via _render_html_document()) and
    to_epub(), which otherwise duplicated this loop identically."""
    for story in stories:
        try:
            story.body_html = _inline_story_images(story.body_html, max_dimension)
        except Exception as err:
            print(f"Sad honk :/ Couldn't process images for {story.headline!r}: {err}")


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
        deduplicate: bool = False,
    ):
        """
        Create a new Goosepaper.

        Arguments:
            story_providers: A list of StoryProvider objects to render
            title: The title of the goosepaper
            subtitle: The subtitle of the goosepaper
            deduplicate: Whether to remove stories with a matching headline and date when
                rendering. Default: False

        """
        self.story_providers = story_providers
        self.title = title if title else "Daily Goosepaper"
        self.subtitle = subtitle + "\n" if subtitle else ""
        self.subtitle += datetime.datetime.today().strftime("%B %d, %Y %H:%M")
        self.deduplicate = deduplicate

    def get_stories(self, deduplicate: bool = None) -> List[Story]:
        """
        Retrieve the complete list of stories to render in this Goosepaper.

        Arguments:
            deduplicate: Whether to remove duplicate stories. Defaults to the value passed to
                the constructor.

        Returns:
            List[Story]

        """
        if deduplicate is None:
            deduplicate = self.deduplicate
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

        image_max_dimension = _image_max_dimension(
            style_obj.get_page_profile(page_profile), effective_columns
        )
        _inline_all_story_images(stories, image_max_dimension)

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
                PlacementPreference.APPENDIX,
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

        appendix_story_objects = [
            story
            for story in stories
            if story.placement_preference == PlacementPreference.APPENDIX
        ]
        ordered_story_objects = (
            utility_story_objects
            + main_story_objects
            + sidebar_story_objects
            + appendix_story_objects
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
        appendix_stories, appendix_toc_entries = self._render_story_region(
            appendix_story_objects,
            story_anchor_ids,
            story_numbers,
            used_anchors=used_anchors,
        )
        toc_html = self._render_table_of_contents(
            utility_toc_entries + main_toc_entries + sidebar_toc_entries + appendix_toc_entries,
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
        appendix_html = ""
        if appendix_stories:
            appendix_html = f"""
                    <div class="appendix">
                        {''.join(appendix_stories)}
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
                {appendix_html}
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

        # Unlike to_html()/to_pdf(), there's no page_profile/layout here to size images off of -
        # an epub's text reflows to whatever screen/font size the reader uses. _IMAGE_DIMENSION_
        # FALLBACK is a flat, reasonable cap for that "unknown target" case (the same value used
        # elsewhere when a page_profile can't be parsed), rather than leaving every story
        # provider's remote image links completely unprocessed.
        _inline_all_story_images(stories, _IMAGE_DIMENSION_FALLBACK)

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
