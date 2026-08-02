from typing import List

from .storyprovider import StoryProvider
from ..story import Story


class SectionProvider(StoryProvider):
    """Wraps any other StoryProvider and tags each of its stories with a section - the group
    heading Goosepaper renders stories under (see Goosepaper._story_runs/_render_story_region).
    Providers themselves know nothing about sections; this is how a caller assembling a paper out
    of several providers assigns each one to a named group.

    `headline_prefix`, if given, is prepended to every returned headline - useful for providers
    whose stories otherwise wouldn't say which instance they came from (e.g. two weather
    providers for two different locations, both returning the bare headline "Weather").
    """

    def __init__(self, inner: StoryProvider, section_title: str, headline_prefix: str = "") -> None:
        self._inner = inner
        self._section_title = section_title
        self._headline_prefix = headline_prefix

    def get_stories(self) -> List[Story]:
        stories = self._inner.get_stories()
        for story in stories:
            story.section_title = self._section_title
            if self._headline_prefix:
                story.headline = f"{self._headline_prefix}: {story.headline}"
        return stories
