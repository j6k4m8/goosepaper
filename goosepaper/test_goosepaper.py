from .goosepaper import Goosepaper
from .story import Story
from .styles import Style
from .util import PlacementPreference

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
    assert '<li>' not in html
    assert 'href="#story-1-lorem-ipsum-dolor-sit-amet"' in html
    assert 'id="story-1-lorem-ipsum-dolor-sit-amet"' in html
    assert '"Literata", serif' in html
    assert "size: 210mm 297mm;" in html
    assert 'class="stories stories--1col"' in html


def test_toc_is_omitted_by_default():
    g = Goosepaper([LoremStoryProvider(limit=2)])

    html = g.to_html()

    assert '<nav class="table-of-contents' not in html


def test_toc_can_collapse_sections_and_skip_opted_out_stories():
    class MixedProvider:
        def get_stories(self):
            return [
                Story(headline="Lead story", body_text="Lead body"),
                Story(
                    headline="Jordan at 2026-04-24 15:30",
                    body_text="Sky body one",
                    section_title="Bluesky",
                    short_form=True,
                ),
                Story(
                    headline="Jordan at 2026-04-24 16:00",
                    body_text="Sky body two",
                    section_title="Bluesky",
                    short_form=True,
                ),
                Story(
                    headline="Hidden from contents",
                    body_text="Hidden body",
                    include_in_toc=False,
                ),
            ]

    g = Goosepaper([MixedProvider()])

    html = g.to_html(table_of_contents=True)

    assert html.count('class="table-of-contents__entry"') == 2
    assert 'href="#story-1-lead-story"' in html
    assert 'href="#section-bluesky"' in html
    assert 'href="#story-2-jordan-at-2026-04-24-15-30"' not in html
    assert 'href="#story-4-hidden-from-contents"' not in html
    assert 'id="section-bluesky"' in html
    assert 'class="story-section-title">Bluesky<' in html
    assert 'class="story story-card story-short"' in html
    assert 'Hidden from contents' in html


def test_utility_strip_renders_between_header_and_contents():
    class UtilityProvider:
        def get_stories(self):
            return [
                Story(
                    headline="Weather",
                    body_html="<p>Forecast strip</p>",
                    placement_preference=PlacementPreference.UTILITY,
                    include_in_toc=False,
                    short_form=True,
                ),
                Story(headline="Lead story", body_text="Lead body"),
            ]

    g = Goosepaper([UtilityProvider()])

    html = g.to_html(table_of_contents=True)

    assert 'class="utility-strip"' in html
    assert html.index('class="utility-strip"') < html.index('class="table-of-contents')
    assert html.index('class="table-of-contents') < html.index('class="stories ')
    assert 'class="story story-card placement-utility story-short"' in html


def test_style_resolves_auto_columns_from_page_profile():
    academy = Style("Academy")
    avenue = Style("FifthAvenue")
    maiden = Style("GrayMaiden")

    assert academy.resolve_column_count(layout="auto", page_profile="remarkable2") == 1
    assert avenue.resolve_column_count(layout="auto", page_profile="remarkable2") == 2
    assert avenue.resolve_column_count(layout="auto", page_profile="a4") == 2
    assert maiden.resolve_column_count(layout="auto", page_profile="remarkable2") == 2
    assert avenue.resolve_column_count(layout="3col", page_profile="a4") == 3


def test_graymaiden_style_loads_editorial_masthead_assets():
    style = Style("GrayMaiden")

    css = style.get_css(layout="auto", page_profile="rm1")

    assert "UnifrakturMaguntia" in css
    assert "Newsreader" in css
    assert "Source Serif 4" in css
    assert "leader(dotted)" in css
    assert "target-counter(attr(href), page)" in css
    assert "UnifrakturCook" not in css
    assert style.get_stylesheets()
