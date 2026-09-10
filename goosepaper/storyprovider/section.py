from typing import List

from .storyprovider import StoryProvider
from ..story import Story


class SectionProvider(StoryProvider):
    """Wraps any other StoryProvider and tags each of its stories with a section - the group
    heading Goosepaper renders stories under (see Goosepaper._story_runs/_render_story_region).
    Providers themselves know nothing about sections; this is how a caller assembling a paper out
    of several providers assigns each one to a named group.

    section_heading_visible=False keeps the section's stories in the table of contents while
    hiding the heading itself from the rendered page - for a group whose content already carries
    its own visual identity (a comic strip with its title drawn into the image) and doesn't need
    it repeated as running text. Named to match Story.section_heading_visible exactly (the
    attribute this sets on every wrapped story) rather than a shorter "heading_visible" - Story
    also has an unrelated, separately-named headline_visible (a single story's own headline, see
    the comic provider), and a bare "heading" here would be ambiguous between the two.
    """

    def __init__(
        self,
        inner: StoryProvider,
        section_title: str,
        section_heading_visible: bool = True,
    ) -> None:
        self._inner = inner
        self._section_title = section_title
        self._section_heading_visible = section_heading_visible

    def get_stories(self) -> List[Story]:
        stories = self._inner.get_stories()
        for story in stories:
            story.section_title = self._section_title
            story.section_heading_visible = self._section_heading_visible
        return stories
