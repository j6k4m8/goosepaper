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
    ) -> None:
        """
        Create a new Story with headline and body text.
        """
        self.headline = headline
        self.priority = priority
        self.byline = byline
        self.date = date
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
        if extra_classes:
            classes.extend(extra_classes)
        headline = (
            f"<{headline_tag} class='story-headline {priority_class}'>{escape(self.headline)}</{headline_tag}>"
            if self.headline
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
