from typing import List

from .storyprovider import StoryProvider
from ..story import Story


class SectionProvider(StoryProvider):
    """Wraps any other StoryProvider and tags each of its stories with a section - the group
    heading Goosepaper renders stories under (see Goosepaper._story_runs/_render_story_region).
    Providers themselves know nothing about sections; this is how a caller assembling a paper out
    of several providers assigns each one to a named group.

    heading_visible=False keeps the section's stories in the table of contents while hiding the
    heading itself from the rendered page - for a group whose content already carries its own
    visual identity (a comic strip with its title drawn into the image) and doesn't need it
    repeated as running text.
    """

    def __init__(
        self,
        inner: StoryProvider,
        section_title: str,
        heading_visible: bool = True,
    ) -> None:
        self._inner = inner
        self._section_title = section_title
        self._heading_visible = heading_visible

    def get_stories(self) -> List[Story]:
        stories = self._inner.get_stories()
        for story in stories:
            story.section_title = self._section_title
            story.section_heading_visible = self._heading_visible
        return stories
