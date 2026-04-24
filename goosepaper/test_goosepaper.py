from .goosepaper import Goosepaper
from .styles import Style

from .storyprovider.storyprovider import LoremStoryProvider


def test_can_create_goosepaper_with_no_providers():
    g = Goosepaper([])
    assert g.story_providers == []


def test_can_create_goosepaper_with_duplicate_provider():
    g = Goosepaper([LoremStoryProvider(limit=3), LoremStoryProvider(limit=4)])
    assert len(g.get_stories()) == 7


def test_can_deduplicate_by_headline():
    g = Goosepaper([LoremStoryProvider(limit=3), LoremStoryProvider(limit=4)])
    assert len(g.get_stories(deduplicate=True)) == 1


def test_skips_failing_providers_and_keeps_rendering():
    class BrokenProvider:
        def get_stories(self):
            raise RuntimeError("boom")

    g = Goosepaper([BrokenProvider(), LoremStoryProvider(limit=2)])

    stories = g.get_stories()

    assert len(stories) == 2


def test_can_create_html():
    g = Goosepaper([LoremStoryProvider()])
    assert "<html>" in g.to_html()
    assert "Lorem ipsum" in g.to_html()


def test_html_render_includes_theme_css_and_layout():
    g = Goosepaper([LoremStoryProvider(limit=3)])
    html = g.to_html(
        style="Academy",
        font_size=15,
        body_font="Literata",
        table_of_contents=True,
        layout="1col",
        page_profile="a4",
    )

    assert 'class="header"' in html
    assert 'class="table-of-contents table-of-contents--1col"' in html
    assert 'href="#story-1-lorem-ipsum-dolor-sit-amet"' in html
    assert 'id="story-1-lorem-ipsum-dolor-sit-amet"' in html
    assert '"Literata", serif' in html
    assert "size: 210mm 297mm;" in html
    assert 'class="stories stories--1col"' in html


def test_toc_is_omitted_by_default():
    g = Goosepaper([LoremStoryProvider(limit=2)])

    html = g.to_html()

    assert '<nav class="table-of-contents' not in html


def test_style_resolves_auto_columns_from_page_profile():
    academy = Style("Academy")
    avenue = Style("FifthAvenue")

    assert academy.resolve_column_count(layout="auto", page_profile="remarkable2") == 1
    assert avenue.resolve_column_count(layout="auto", page_profile="remarkable2") == 2
    assert avenue.resolve_column_count(layout="auto", page_profile="a4") == 2
    assert avenue.resolve_column_count(layout="3col", page_profile="a4") == 3
