import pytest

from .goosepaper import Goosepaper

from .storyprovider import LoremStoryProvider


def test_cannot_create_goosepaper_without_args():
    with pytest.raises(TypeError):
        g = Goosepaper()


def test_can_create_goosepaper_with_no_providers():
    g = Goosepaper([])
    assert g.story_providers == []


def test_can_create_goosepaper_with_duplicate_provider():
    g = Goosepaper([LoremStoryProvider(limit=3), LoremStoryProvider(limit=4)])
    assert len(g.get_stories()) == 7


def test_can_deduplicate_by_headline():
    g = Goosepaper([LoremStoryProvider(limit=3), LoremStoryProvider(limit=4)])
    assert len(g.get_stories(deduplicate=True)) == 1


def test_can_create_html():
    g = Goosepaper([LoremStoryProvider()])
    assert "<html>" in g.to_html()
    assert "Lorem ipsum" in g.to_html()
