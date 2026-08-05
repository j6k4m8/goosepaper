from typing import List

from .storyprovider import StoryProvider
from ..story import Story


class SectionProvider(StoryProvider):
    """Wraps any other StoryProvider and tags each of its stories with a section - the group
    heading Goosepaper renders stories under (see Goosepaper._story_runs/_render_story_region).
    Providers themselves know nothing about sections; this is how a caller assembling a paper out
    of several providers assigns each one to a named group.
    """

    def __init__(self, inner: StoryProvider, section_title: str) -> None:
        self._inner = inner
        self._section_title = section_title

    def get_stories(self) -> List[Story]:
        stories = self._inner.get_stories()
        for story in stories:
            story.section_title = self._section_title
        return stories
