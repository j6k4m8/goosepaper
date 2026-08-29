from .section import SectionProvider
from .storyprovider import StoryProvider
from ..story import Story


class _FakeProvider(StoryProvider):
    def __init__(self, stories):
        self._stories = stories

    def get_stories(self):
        return self._stories


def test_section_provider_tags_every_story_with_the_section_title():
    inner = _FakeProvider(
        [Story("One", body_text="a"), Story("Two", body_text="b")]
    )
    provider = SectionProvider(inner, "Tech News")
    stories = provider.get_stories()

    assert [s.section_title for s in stories] == ["Tech News", "Tech News"]


def test_section_provider_leaves_headlines_unchanged():
    inner = _FakeProvider([Story("Original headline", body_text="a")])
    provider = SectionProvider(inner, "Weather")
    stories = provider.get_stories()

    assert stories[0].headline == "Original headline"


def test_section_provider_defaults_heading_to_visible():
    inner = _FakeProvider([Story("One", body_text="a")])
    provider = SectionProvider(inner, "Tech News")
    stories = provider.get_stories()

    assert stories[0].section_heading_visible is True


def test_section_provider_tags_every_story_with_section_heading_visible_false():
    inner = _FakeProvider(
        [Story("One", body_text="a"), Story("Two", body_text="b")]
    )
    provider = SectionProvider(inner, "Comics", section_heading_visible=False)
    stories = provider.get_stories()

    assert [s.section_heading_visible for s in stories] == [False, False]
