import base64
import io

from PIL import Image

from . import goosepaper as goosepaper_module
from .goosepaper import Goosepaper, _image_max_dimension, _inline_story_images
from .story import Story
from .styles import PageProfile, Style
from .util import PlacementPreference

from .storyprovider import comic, readwise
from .storyprovider.storyprovider import LoremStoryProvider


def _image_bytes(fmt: str, mode: str = "RGB", size=(4, 3), color=(200, 50, 10)) -> bytes:
    image = Image.new(mode, size, color if mode != "L" else 128)
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def _decode_data_uri_image(html: str) -> Image.Image:
    prefix = "data:image/jpeg;base64,"
    start = html.index(prefix) + len(prefix)
    end = html.index('"', start)
    return Image.open(io.BytesIO(base64.b64decode(html[start:end])))


class _FakeResponse:
    def __init__(self, content: bytes, headers: dict = None, ok: bool = True):
        self.content = content
        self.headers = headers or {}
        self._ok = ok

    def raise_for_status(self):
        if not self._ok:
            raise RuntimeError("boom")


class _FixedBodyProvider:
    """A minimal story provider for image-inlining tests - LoremStoryProvider has no way to set
    a custom body_html."""

    def __init__(self, body_html: str, headline: str = "Fixed"):
        self.body_html = body_html
        self.headline = headline

    def get_stories(self):
        return [Story(headline=self.headline, body_html=self.body_html)]


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


def test_appendix_stories_render_after_stories_in_their_own_block():
    class AppendixProvider:
        def get_stories(self):
            return [
                Story(headline="Lead story", body_text="Lead body"),
                Story(
                    headline="Puzzle solution",
                    body_html="<p>42</p>",
                    placement_preference=PlacementPreference.APPENDIX,
                    include_in_toc=False,
                    short_form=True,
                ),
            ]

    g = Goosepaper([AppendixProvider()])

    html = g.to_html()

    assert 'class="appendix"' in html
    assert html.index('class="stories ') < html.index('class="appendix"')
    assert 'class="story story-card placement-appendix story-short"' in html
    # Not duplicated into the main column flow.
    main_stories_html = html.split('class="main-stories"')[1].split("</div>")[0]
    assert "Puzzle solution" not in main_stories_html


def test_appendix_stories_with_identical_headline_are_deduplicated():
    """A shared appendix explanation (e.g. "how does Sudoku work?") requested by several
    puzzle sources of the same type should only appear once, not once per source. No new
    dedup mechanism needed for this - Goosepaper.get_stories(deduplicate=True) already
    collapses same-headline/same-date stories, and Story's `date` defaults to None, so two
    independently-constructed explanation Story objects with the same headline and no
    explicit date are equal for dedup purposes as long as their headline matches exactly."""

    class RepeatedAppendixProvider:
        def get_stories(self):
            return [
                Story(headline=f"Sudoku puzzle {i}", body_text=f"Puzzle {i}")
                for i in range(2)
            ] + [
                Story(
                    headline="How does Sudoku work?",
                    body_html="<p>Fill the grid so every row, column and box has 1-9.</p>",
                    placement_preference=PlacementPreference.APPENDIX,
                    include_in_toc=False,
                    short_form=True,
                )
                for _ in range(2)
            ]

    g = Goosepaper([RepeatedAppendixProvider()])

    stories = g.get_stories(deduplicate=True)
    appendix_stories = [
        s for s in stories if s.placement_preference == PlacementPreference.APPENDIX
    ]
    assert len(appendix_stories) == 1
    assert len(stories) == 3  # 2 puzzles + 1 deduplicated appendix explanation

    # to_html()/to_pdf() only dedupe if a caller explicitly requests it. get_stories() defaults
    # to deduplicate=None, which falls back to the Goosepaper instance's own `deduplicate`
    # constructor argument (default False) - see test_to_html_* below for that path.


def test_to_html_deduplicates_when_constructor_flag_is_set():
    g = Goosepaper([LoremStoryProvider(limit=3)], deduplicate=True)
    html = g.to_html()
    assert html.count("Lorem Ipsum Dolor Sit Amet") == 1


def test_to_html_does_not_deduplicate_by_default():
    g = Goosepaper([LoremStoryProvider(limit=3)])
    html = g.to_html()
    assert html.count("Lorem Ipsum Dolor Sit Amet") == 3


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


# --- Render-time image sizing: _image_max_dimension / _inline_story_images ---------------------


def test_image_max_dimension_shrinks_with_more_columns():
    profile = PageProfile(
        name="test",
        size="10in 12in",
        margin_top="0in",
        margin_right="0in",
        margin_bottom="0in",
        margin_left="0in",
        max_auto_columns=3,
    )
    one_col = _image_max_dimension(profile, effective_columns=1)
    two_col = _image_max_dimension(profile, effective_columns=2)
    # 10in content width at 200 DPI = 2000px for 1 column, 1000px for 2 columns.
    assert one_col == 2000
    assert two_col == 1000


def test_image_max_dimension_accounts_for_margins_and_mm_units():
    profile = PageProfile(
        name="a4-like",
        size="210mm 297mm",
        margin_top="10mm",
        margin_right="10mm",
        margin_bottom="10mm",
        margin_left="10mm",
        max_auto_columns=1,
    )
    # (210mm - 20mm) / 25.4 = 7.48in content width, * 200 DPI.
    assert _image_max_dimension(profile, effective_columns=1) == round(190 / 25.4 * 200)


def test_image_max_dimension_never_goes_below_the_floor():
    tiny_profile = PageProfile(
        name="tiny",
        size="1in 1in",
        margin_top="0.4in",
        margin_right="0.4in",
        margin_bottom="0.4in",
        margin_left="0.4in",
        max_auto_columns=1,
    )
    assert _image_max_dimension(tiny_profile, effective_columns=1) == 400


def test_image_max_dimension_falls_back_on_unparseable_size():
    bad_profile = PageProfile(
        name="bad",
        size="huge",
        margin_top="0in",
        margin_right="0in",
        margin_bottom="0in",
        margin_left="0in",
        max_auto_columns=1,
    )
    assert _image_max_dimension(bad_profile, effective_columns=1) == 1200


def test_inline_story_images_fetches_and_normalizes_a_remote_http_image(monkeypatch):
    fake_png = _image_bytes("PNG", size=(50, 40))
    seen_urls = []

    def fake_get(url, *, headers, timeout):
        seen_urls.append(url)
        return _FakeResponse(fake_png)

    monkeypatch.setattr(goosepaper_module.requests, "get", fake_get)

    result = _inline_story_images(
        '<p>hi</p><img src="https://example.com/photo.png">', max_dimension=20
    )

    assert seen_urls == ["https://example.com/photo.png"]
    assert "data:image/jpeg;base64," in result
    assert "https://example.com/photo.png" not in result
    embedded = _decode_data_uri_image(result)
    assert max(embedded.size) == 20  # capped to max_dimension, aspect preserved


def test_inline_story_images_re_encodes_an_already_inlined_data_uri(monkeypatch):
    """A provider (or an earlier render pass) may hand back a story whose image is already a
    data: URI rather than a remote link - CMYK/oversized/format normalization must still apply
    there too, not just to freshly-fetched remote http(s) images."""

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not run for an already-inlined image")

    monkeypatch.setattr(goosepaper_module.requests, "get", fail_get)

    fake_cmyk_jpeg = _image_bytes("JPEG", mode="CMYK", size=(8, 8))
    src = f"data:image/jpeg;base64,{base64.b64encode(fake_cmyk_jpeg).decode('ascii')}"
    result = _inline_story_images(f'<img src="{src}">', max_dimension=1200)

    embedded = _decode_data_uri_image(result)
    assert embedded.format == "JPEG"
    assert embedded.mode in ("RGB", "L")


def test_inline_story_images_leaves_a_failing_image_untouched(monkeypatch):
    def fake_get(url, *, headers, timeout):
        raise RuntimeError("network's down")

    monkeypatch.setattr(goosepaper_module.requests, "get", fake_get)

    html = '<img src="https://example.com/broken.jpg">'
    assert _inline_story_images(html, max_dimension=1200) == html


def test_inline_story_images_leaves_an_http_error_response_untouched(monkeypatch):
    """Same failure-tolerance guarantee as the connection-error case above, but via a response
    that comes back successfully at the transport level and only fails raise_for_status() -
    the only test that actually exercises _FakeResponse's ok=False branch."""
    monkeypatch.setattr(
        goosepaper_module.requests, "get", lambda url, *, headers, timeout: _FakeResponse(b"", ok=False)
    )

    html = '<img src="https://example.com/gone.jpg">'
    assert _inline_story_images(html, max_dimension=1200) == html


def test_inline_story_images_leaves_an_undecodable_response_untouched(monkeypatch):
    """A response that succeeds (HTTP 200) but isn't actual image data - e.g. an anti-bot HTML
    interstitial served where comic.py's resolved strip URL was expected - must be left
    untouched like any other failure, not raise out of _inline_story_images or embed garbage."""
    monkeypatch.setattr(
        goosepaper_module.requests,
        "get",
        lambda url, *, headers, timeout: _FakeResponse(b"<html><body>Access denied</body></html>"),
    )

    html = '<img src="https://example.com/not-actually-an-image.jpg">'
    assert _inline_story_images(html, max_dimension=1200) == html


def test_inline_story_images_skips_relative_and_missing_src():
    html = '<img src="/relative.jpg"><img>'
    assert _inline_story_images(html, max_dimension=1200) == html


def test_inline_story_images_preserves_a_leading_style_block(monkeypatch):
    """Regression test for the real shape comic.py's body_html has: a bare <style> tag followed
    by a <div>, not wrapped in any container (see comic._COMIC_CSS + get_stories()) - see
    _inline_story_images's own comment on the head/body relocation this triggers in lxml."""
    fake_png = _image_bytes("PNG", size=(10, 8))
    monkeypatch.setattr(
        goosepaper_module.requests, "get", lambda url, *, headers, timeout: _FakeResponse(fake_png)
    )

    body_html = (
        comic._COMIC_CSS
        + '<div class="comic-strip-body">'
        + '<img class="comic-strip" src="https://example.com/strip.png" alt="XKCD" />'
        + "</div>"
    )

    result = _inline_story_images(body_html, max_dimension=1200)

    assert ".comic-strip-body { text-align: center; }" in result
    assert "data:image/jpeg;base64," in result
    assert "https://example.com/strip.png" not in result


def test_render_html_document_inlines_images_from_a_real_comic_story(monkeypatch):
    """Goes one step further than the hand-built body_html above: runs the actual
    DailyComicStoryProvider.get_stories() - not a stand-in for its <style>+<div> shape - through
    a real Goosepaper.to_html(), to catch any future drift between comic._COMIC_CSS's real
    structure and what a hand-copied fixture assumes it looks like."""
    xkcd_html = b"""
    <html><body>
    <div id="comic">
    <img src="//imgs.xkcd.com/comics/todays_strip.png" title="hover joke" alt="Todays Strip"/>
    </div>
    </body></html>
    """
    fake_png = _image_bytes("PNG", size=(50, 40))

    def fake_get(url, *, headers=None, timeout=None):
        if url == "https://xkcd.com":
            return _FakeResponse(xkcd_html)
        return _FakeResponse(fake_png)

    monkeypatch.setattr(comic.requests, "get", fake_get)
    monkeypatch.setattr(goosepaper_module.requests, "get", fake_get)

    provider = comic.DailyComicStoryProvider(comic_type="xkcd")
    g = Goosepaper([provider])

    html = g.to_html(page_profile="remarkable2", layout="1col")

    assert ".comic-strip-body { text-align: center; }" in html
    assert "data:image/jpeg;base64," in html
    assert "https://imgs.xkcd.com/comics/todays_strip.png" not in html


def test_render_html_document_inlines_images_from_any_story_provider(monkeypatch):
    """Image inlining applies uniformly to every story provider (a plain Story with an <img>,
    not just RSS/comic), because it happens once here rather than being opt-in per provider."""
    fake_png = _image_bytes("PNG", size=(50, 40))
    monkeypatch.setattr(
        goosepaper_module.requests, "get", lambda url, *, headers, timeout: _FakeResponse(fake_png)
    )

    provider = _FixedBodyProvider('<img src="https://example.com/photo.png">')
    g = Goosepaper([provider])

    html = g.to_html(page_profile="remarkable2", layout="1col")

    assert "data:image/jpeg;base64," in html
    assert "https://example.com/photo.png" not in html


def test_render_html_document_isolates_a_failing_storys_image_inlining(monkeypatch):
    """A failure processing one story's images must not take the whole render down with it -
    the deleted rss.py call site used to guarantee this per-story; _render_html_document()'s own
    loop needs the same guarantee now that it runs for every story instead of just RSS ones.

    The fault is injected at the actual boundary _inline_story_images can realistically fail at
    (parsing untrusted body_html via bs4/lxml) rather than by replacing the private function
    itself, so this stays meaningful across internal refactors of that function."""
    real_soup = goosepaper_module.bs4.BeautifulSoup

    def flaky_soup(body_html, *args, **kwargs):
        if "boom" in body_html:
            raise ValueError("simulated bs4/lxml parse failure")
        return real_soup(body_html, *args, **kwargs)

    monkeypatch.setattr(goosepaper_module.bs4, "BeautifulSoup", flaky_soup)

    broken = _FixedBodyProvider("<p>boom</p>", headline="Broken story")
    fine = _FixedBodyProvider("<p>All good</p>", headline="Fine story")
    g = Goosepaper([broken, fine])

    html = g.to_html()

    assert "Broken story" in html
    assert "<p>boom</p>" in html
    assert "Fine story" in html
    assert "<p>All good</p>" in html


def test_render_html_document_sizes_images_smaller_for_a_smaller_page_profile(monkeypatch):
    fake_png = _image_bytes("PNG", size=(3000, 2000))
    monkeypatch.setattr(
        goosepaper_module.requests, "get", lambda url, *, headers, timeout: _FakeResponse(fake_png)
    )

    small_html = Goosepaper([_FixedBodyProvider('<img src="https://example.com/p.png">')]).to_html(
        page_profile="paper_pro_move", layout="1col"
    )
    large_html = Goosepaper([_FixedBodyProvider('<img src="https://example.com/p.png">')]).to_html(
        page_profile="letter", layout="1col"
    )

    assert max(_decode_data_uri_image(small_html).size) < max(_decode_data_uri_image(large_html).size)


def test_render_html_document_inlines_images_from_a_real_readwise_story(monkeypatch):
    """Goes one step further than the synthetic-provider test above: Mastodon/Bluesky/Reddit
    never put an <img> in body_html at all (Bluesky/Reddit only extract plain text fields;
    Mastodon's attached media rides in a separate <media:content> RSS element this provider's
    code doesn't read) - Readwise Reader is the one built-in provider whose real code path can
    carry an image today, since body_source="html" preserves <img> tags from the saved article's
    real html_content (img isn't in _DROP_TAGS - see readwise.py).

    Runs the actual ReadwiseReaderStoryProvider.get_stories() - not a stand-in - through its own
    existing no-credentials mock (matching test_readwise.py's own pattern) and into a real
    Goosepaper.to_html(), to prove the image-inlining path works end to end for a real provider,
    not just the synthetic _FixedBodyProvider used elsewhere in this file.
    """
    fake_png = _image_bytes("PNG", size=(50, 40))

    class _FakeReadwiseResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [
                    {
                        "id": "doc-1",
                        "title": "A saved article",
                        "author": "Ada Lovelace",
                        "site_name": "Example",
                        "reading_time": "4 mins",
                        "published_date": "2026-04-24",
                        "saved_at": "2026-04-25T10:15:00+00:00",
                        "summary": "fallback",
                        "html_content": (
                            "<article><h1>A saved article</h1>"
                            "<p>Look at this:</p>"
                            '<img src="https://example.com/article-photo.png">'
                            "</article>"
                        ),
                        "parent_id": None,
                    }
                ],
                "nextPageCursor": None,
            }

    def fake_get(url, *args, **kwargs):
        if url == "https://readwise.io/api/v3/list/":
            return _FakeReadwiseResponse()
        return _FakeResponse(fake_png)

    monkeypatch.setenv("READWISE_TOKEN", "test-token")
    # readwise.requests and goosepaper_module.requests are the same module object (Python caches
    # imports) - patching .get once covers both the Readwise API call and the later image fetch.
    monkeypatch.setattr(readwise.requests, "get", fake_get)

    provider = readwise.ReadwiseReaderStoryProvider(body_source="html")
    g = Goosepaper([provider])

    html = g.to_html(page_profile="remarkable2", layout="1col")

    assert "data:image/jpeg;base64," in html
    assert "https://example.com/article-photo.png" not in html


def test_to_epub_also_inlines_images(monkeypatch):
    """to_epub() doesn't route through _render_html_document() (no page_profile/layout exists
    for a reflowable epub), so it needs its own call to _inline_all_story_images() - otherwise
    every provider's remote image links would reach the epub completely unprocessed."""
    import zipfile

    fake_png = _image_bytes("PNG", size=(3000, 2000))
    monkeypatch.setattr(
        goosepaper_module.requests, "get", lambda url, *, headers, timeout: _FakeResponse(fake_png)
    )

    provider = _FixedBodyProvider(
        '<img src="https://example.com/photo.png">', headline="An article"
    )
    g = Goosepaper([provider])

    buf = io.BytesIO()
    g.to_epub(buf)
    buf.seek(0)

    with zipfile.ZipFile(buf) as archive:
        chapters = [
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.endswith(".xhtml")
        ]
    combined = "\n".join(chapters)

    assert "data:image/jpeg;base64," in combined
    assert "https://example.com/photo.png" not in combined
    embedded = _decode_data_uri_image(combined)
    # Capped to _IMAGE_DIMENSION_FALLBACK (1200), same as any page_profile that can't be parsed.
    assert max(embedded.size) == 1200
