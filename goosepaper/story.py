import datetime

from .util import PlacementPreference, htmlize, StoryPriority


class Story:
    def __init__(
        self,
        headline: str,
        body_html: str = None,
        body_text: str = None,
        byline: str = None,
        date: datetime.datetime = None,
        priority: int = StoryPriority.DEFAULT,
        placement_preference: PlacementPreference = PlacementPreference.NONE,
    ) -> None:
        """
        Create a new Story with headline and body text.
        """
        self.headline = headline
        self.priority = priority
        self.byline = byline
        self.date = date
        self.body_html = body_html if body_html else htmlize(body_text)
        self.placement_preference = placement_preference


    def __gt__(self, other):
        if not self.date: return False
        if not other.date: return True
        return self.date > other.date


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
