import datetime
from html import escape
from typing import List, Optional, Union

import bs4

from .util import PlacementPreference, htmlize, StoryPriority


class Story:
    def __init__(
        self,
        headline: Optional[str],
        body_html: str = None,
        body_text: Union[str, List[str]] = None,
        byline: str = None,
        date: datetime.datetime = None,
        priority: StoryPriority = StoryPriority.DEFAULT,
        placement_preference: PlacementPreference = PlacementPreference.NONE,
        include_in_toc: bool = True,
        section_title: Optional[str] = None,
        section_heading_visible: bool = True,
        headline_visible: bool = True,
        short_form: bool = False,
    ) -> None:
        """
        Create a new Story with headline and body text.
        """
        self.headline = headline
        self.priority = priority
        self.byline = byline
        self.date = date
        self.include_in_toc = include_in_toc
        self.section_title = section_title
        # Only meaningful when section_title is set - False keeps this story's section run
        # out of the visible body text (see Goosepaper._render_story_region) while still
        # letting it contribute a table-of-contents entry, for content that already carries
        # its own visual identity (e.g. a comic strip with its title drawn into the image
        # itself) and doesn't need the section heading repeated in the page flow.
        self.section_heading_visible = section_heading_visible
        # False keeps `headline` around for everything that still needs the text itself
        # (anchor-id slugging, its own table-of-contents entry when there's no section_title,
        # deduplicate=True's headline-based matching) while suppressing only the rendered
        # <h1>/<h2>/... tag in to_html() - for content that already carries its own visible
        # identity (e.g. DailyComicStoryProvider's strip image, whose alt text already names it)
        # and doesn't need that name repeated as running text above it too.
        self.headline_visible = headline_visible
        self.short_form = short_form
        if body_html is not None:
            self.body_html = body_html
        elif body_text is not None:
            self.body_html = htmlize(body_text)
        else:
            raise ValueError(
                "You must provide at least one of body_html or body_text "
                "to the Story constructor"
            )
        self.placement_preference = placement_preference

    def priority_class(self) -> str:
        return {
            StoryPriority.DEFAULT: "",
            StoryPriority.LOW: "priority-low",
            StoryPriority.HEADLINE: "priority-headline",
            StoryPriority.BANNER: "priority-banner",
        }[self.priority]

    def placement_class(self) -> str:
        return {
            PlacementPreference.NONE: "",
            PlacementPreference.FULLPAGE: "placement-fullpage",
            PlacementPreference.SIDEBAR: "placement-sidebar",
            PlacementPreference.EAR: "placement-ear",
            PlacementPreference.FOLIO: "placement-folio",
            PlacementPreference.BANNER: "placement-banner",
            PlacementPreference.UTILITY: "placement-utility",
            PlacementPreference.APPENDIX: "placement-appendix",
        }[self.placement_preference]

    def plain_text(self) -> str:
        return bs4.BeautifulSoup(self.body_html, "lxml").get_text(" ", strip=True)

    def word_count(self) -> int:
        return len(self.plain_text().split())

    def to_html(
        self,
        headline_tag: str = "h1",
        extra_classes: Optional[List[str]] = None,
        prefix_html: str = "",
        anchor_id: Optional[str] = None,
    ) -> str:
        priority_class = self.priority_class()
        placement_class = self.placement_class()
        classes = ["story", "story-card"]
        if priority_class:
            classes.append(priority_class)
        if placement_class:
            classes.append(placement_class)
        if self.short_form:
            classes.append("story-short")
        if extra_classes:
            classes.extend(extra_classes)
        headline = (
            f"<{headline_tag} class='story-headline {priority_class}'>{escape(self.headline)}</{headline_tag}>"
            if self.headline and self.headline_visible
            else ""
        )
        byline_p = (
            f"<p class='byline'>{escape(self.byline)}</p>"
            if self.byline
            else ""
        )
        anchor_attr = f' id="{escape(anchor_id)}"' if anchor_id else ""
        return f"""
        <article{anchor_attr} class="{' '.join(filter(None, classes))}">
            {prefix_html}
            {headline}
            {byline_p}
            <div class="story-body">{self.body_html}</div>
        </article>
        """
