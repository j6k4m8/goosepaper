import datetime
from typing import List, Optional, Union

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

    def to_html(self) -> str:
        byline_h4 = f"<h4 class='byline'>{self.byline}</h4>" if self.byline else ""
        priority_class = {
            StoryPriority.DEFAULT: "",
            StoryPriority.LOW: "priority-low",
            StoryPriority.BANNER: "priority-banner",
        }[self.priority]
        headline = (
            f"<h1 class='{priority_class}'>{self.headline}</h1>"
            if self.headline
            else ""
        )
        return f"""
        <article class="story">
            {headline}
            {byline_h4}
            {self.body_html}
        </article>
        """
