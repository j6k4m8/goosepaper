import base64
import datetime
import io
from types import SimpleNamespace

from PIL import Image

from . import rss


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


def _feed_entry(
    *,
    title="Feed title",
    summary="<p>Feed summary</p>",
    link="https://example.com/story",
    content=None,
):
    payload = {
        "title": title,
        "updated_parsed": datetime.datetime(
            2026,
            4,
            23,
            9,
            0,
            0,
        ).timetuple(),
    }
    if summary is not None:
        payload["summary"] = summary
    if link is not None:
        payload["link"] = link
    if content is not None:
        payload["content"] = content
    return rss.feedparser.FeedParserDict(payload)


class _FakeResponse:
    def __init__(
        self,
        *,
        ok=True,
        text="<html></html>",
        content=b"<html></html>",
        encoding="utf-8",
        url="https://example.com/story",
    ):
        self.ok = ok
        self.text = text
        self.content = content
        self.encoding = encoding
        self.url = url

    def raise_for_status(self):
        if not self.ok:
            raise rss.requests.HTTPError(f"{self.url} returned an error status")


def test_rss_provider_prefers_embedded_feed_content(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    content=[
                        rss.feedparser.FeedParserDict(
                            {"value": "<p>Embedded story body</p>"}
                        )
                    ]
                )
            ]
        ),
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not run when feed content exists")

    monkeypatch.setattr(rss.requests, "get", fail_get)

    provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
    stories = provider.get_stories()

    assert stories[0].headline == "Feed title"
    assert stories[0].body_html == "<p>Embedded story body</p>"
    assert stories[0].byline == "example.com"


def test_rss_provider_summary_mode_uses_feed_summary(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    summary="<p>Feed summary only</p>",
                    content=[
                        rss.feedparser.FeedParserDict(
                            {"value": "<p>Embedded story body</p>"}
                        )
                    ],
                )
            ]
        ),
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not run in summary mode")

    monkeypatch.setattr(rss.requests, "get", fail_get)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        body_source="summary",
    )
    stories = provider.get_stories()

    assert stories[0].body_html == "<p>Feed summary only</p>"


def test_rss_provider_content_mode_uses_feed_content_without_article_fetch(
    monkeypatch,
):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    summary="<p>Feed summary only</p>",
                    content=[
                        rss.feedparser.FeedParserDict(
                            {"value": "<p>Embedded story body</p>"}
                        )
                    ],
                )
            ]
        ),
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not run in content mode")

    monkeypatch.setattr(rss.requests, "get", fail_get)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        body_source="content",
    )
    stories = provider.get_stories()

    assert stories[0].body_html == "<p>Embedded story body</p>"


def test_rss_provider_content_mode_falls_back_to_summary(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[_feed_entry(summary="<p>Feed summary only</p>", content=None)]
        ),
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not run in content mode")

    monkeypatch.setattr(rss.requests, "get", fail_get)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        body_source="content",
    )
    stories = provider.get_stories()

    assert stories[0].body_html == "<p>Feed summary only</p>"


def test_rss_provider_passes_text_to_readability(monkeypatch):
    seen = {}

    class FakeDocument:
        def __init__(self, html):
            seen["html"] = html

        def title(self):
            return "Readable title"

        def summary(self):
            return "<p>Readable summary</p>"

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[_feed_entry(summary=None)]),
    )
    monkeypatch.setattr(
        rss.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(
            ok=True,
            text="<html><body>decoded</body></html>",
            content=b"<html><body>bytes</body></html>",
        ),
    )
    monkeypatch.setattr(rss, "Document", FakeDocument)

    provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
    stories = provider.get_stories()

    assert isinstance(seen["html"], str)
    assert stories[0].headline == "Readable title"
    assert stories[0].body_html == "<p>Readable summary</p>"


def test_rss_provider_prefer_feed_title_overrides_readability_title(monkeypatch):
    class FakeDocument:
        def __init__(self, html):
            pass

        def title(self):
            return "Golem.de"  # e.g. readability returning just the site name

        def summary(self):
            return "<p>Readable summary</p>"

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[_feed_entry(title="The actual headline", summary=None)]),
    )
    monkeypatch.setattr(
        rss.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(ok=True, text="<html></html>"),
    )
    monkeypatch.setattr(rss, "Document", FakeDocument)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        prefer_feed_title=True,
    )
    stories = provider.get_stories()

    assert stories[0].headline == "The actual headline"


def test_rss_provider_prefer_feed_title_defaults_to_false(monkeypatch):
    class FakeDocument:
        def __init__(self, html):
            pass

        def title(self):
            return "Readable title"

        def summary(self):
            return "<p>Readable summary</p>"

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[_feed_entry(summary=None)]),
    )
    monkeypatch.setattr(
        rss.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(ok=True, text="<html></html>"),
    )
    monkeypatch.setattr(rss, "Document", FakeDocument)

    provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
    stories = provider.get_stories()

    assert stories[0].headline == "Readable title"


def test_rss_provider_article_mode_fetches_article_even_when_feed_has_content(
    monkeypatch,
):
    seen = {"requests": 0}

    class FakeDocument:
        def __init__(self, html):
            self.html = html

        def title(self):
            return "Readable title"

        def summary(self):
            return "<p>Readable summary</p>"

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    content=[
                        rss.feedparser.FeedParserDict(
                            {"value": "<p>Embedded story body</p>"}
                        )
                    ]
                )
            ]
        ),
    )

    def fake_get(*args, **kwargs):
        seen["requests"] += 1
        return _FakeResponse(ok=True, text="<html><body>decoded</body></html>")

    monkeypatch.setattr(rss.requests, "get", fake_get)
    monkeypatch.setattr(rss, "Document", FakeDocument)

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        body_source="article",
    )
    stories = provider.get_stories()

    assert seen["requests"] == 1
    assert stories[0].headline == "Readable title"
    assert stories[0].body_html == "<p>Readable summary</p>"


class TestMakeUrlsAbsolute:
    def test_resolves_a_root_relative_image_src(self):
        html = '<img src="/assets/img/webp/29/03/22-2024-car-and-driver-logo.webp">'

        result = rss._make_urls_absolute(
            html, "https://www.caranddriver.com/features/a12345/some-article/"
        )

        assert result == (
            '<img src="https://www.caranddriver.com/assets/img/webp/29/03/'
            '22-2024-car-and-driver-logo.webp"/>'
        )

    def test_resolves_a_page_relative_link_href(self):
        html = '<a href="../other-story/">read more</a>'

        result = rss._make_urls_absolute(
            html, "https://example.com/section/this-story/"
        )

        assert result == (
            '<a href="https://example.com/section/other-story/">read more</a>'
        )

    def test_leaves_already_absolute_urls_alone(self):
        html = '<img src="https://cdn.example.com/foo.jpg">'

        result = rss._make_urls_absolute(html, "https://example.com/story/")

        assert result == html

    def test_resolves_a_protocol_relative_image_src(self):
        # Regression test: matches a real failure seen in production - "Failed to load image at
        # 'file://images.cgames.de/images/gamestar/290/foo.jpg': ... No such file or directory".
        # A protocol-relative URL ("//host/path") parses with a netloc but no scheme, so an
        # earlier version of this function's `urlparse(value).netloc` check mistook it for
        # already-absolute and left it untouched - it then got resolved later against the
        # newspaper's file:// base_url instead of the article's own https:// URL, producing a
        # broken "file://host/path" URL.
        html = '<img src="//images.cgames.de/images/gamestar/290/foo.jpg">'

        result = rss._make_urls_absolute(html, "https://www.gamestar.de/artikel/foo,123.html")

        assert result == '<img src="https://images.cgames.de/images/gamestar/290/foo.jpg"/>'

    def test_leaves_data_uris_alone(self):
        html = '<img src="data:image/png;base64,aGVsbG8=">'

        result = rss._make_urls_absolute(html, "https://example.com/story/")

        assert result == html

    def test_does_not_leak_a_synthetic_body_wrapper(self):
        html = '<p>hello</p><img src="/foo.jpg">'

        result = rss._make_urls_absolute(html, "https://example.com/")

        assert result == '<p>hello</p><img src="https://example.com/foo.jpg"/>'

    def test_noop_when_nothing_needed_absolutizing(self):
        html = "<p>plain text, no urls here</p>"

        result = rss._make_urls_absolute(html, "https://example.com/story/")

        assert result is html

    def test_noop_without_body_or_base_url(self):
        assert rss._make_urls_absolute("", "https://example.com/") == ""
        assert rss._make_urls_absolute("<p>x</p>", "") == "<p>x</p>"


def test_rss_provider_falls_back_to_feed_summary_when_readability_fails(monkeypatch):
    class BrokenDocument:
        def __init__(self, html):
            raise TypeError("boom")

    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[_feed_entry()]),
    )
    monkeypatch.setattr(
        rss.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(ok=True, text="<html></html>"),
    )
    monkeypatch.setattr(rss, "Document", BrokenDocument)

    provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
    stories = provider.get_stories()

    assert stories[0].headline == "Feed title"
    assert stories[0].body_html == "<p>Feed summary</p>"
    assert stories[0].byline == "example.com"


def test_rss_provider_can_hide_all_bylines(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    title="One",
                    content=[rss.feedparser.FeedParserDict({"value": "<p>One</p>"})],
                ),
                _feed_entry(
                    title="Two",
                    content=[rss.feedparser.FeedParserDict({"value": "<p>Two</p>"})],
                ),
            ]
        ),
    )

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        byline="none",
    )
    stories = provider.get_stories()

    assert stories[0].byline is None
    assert stories[1].byline is None


def test_rss_provider_can_show_only_first_byline(monkeypatch):
    monkeypatch.setattr(
        rss.feedparser,
        "parse",
        lambda _: SimpleNamespace(
            entries=[
                _feed_entry(
                    title="One",
                    content=[rss.feedparser.FeedParserDict({"value": "<p>One</p>"})],
                ),
                _feed_entry(
                    title="Two",
                    content=[rss.feedparser.FeedParserDict({"value": "<p>Two</p>"})],
                ),
            ]
        ),
    )

    provider = rss.RSSFeedStoryProvider(
        "https://example.com/feed.xml",
        byline="first",
    )
    stories = provider.get_stories()

    assert stories[0].byline == "example.com"
    assert stories[1].byline is None


class TestInlineRemoteImages:
    """Wiring tests: does _inline_remote_images fetch the right URLs, skip the right ones, and
    tolerate a failure without losing the rest? The actual Pillow re-encode step it delegates to
    (size capping, CMYK/transparency handling) has its own direct tests in test_imageutil.py."""

    def test_inlines_a_remote_http_image_as_a_data_uri(self, monkeypatch):
        fake_png = _image_bytes("PNG", size=(5, 4))
        seen_urls = []

        def fake_get(url, *, headers, timeout):
            seen_urls.append(url)
            return _FakeResponse(ok=True, content=fake_png)

        monkeypatch.setattr(rss.requests, "get", fake_get)

        result = rss._inline_remote_images(
            '<p>hello</p><img src="https://example.com/photo.jpg">'
        )

        assert seen_urls == ["https://example.com/photo.jpg"]
        assert "data:image/jpeg;base64," in result
        assert "https://example.com/photo.jpg" not in result
        embedded = _decode_data_uri_image(result)
        assert embedded.size == (5, 4)

    def test_leaves_data_uri_images_untouched(self, monkeypatch):
        def fail_get(*args, **kwargs):
            raise AssertionError("requests.get should not run for an already-inlined image")

        monkeypatch.setattr(rss.requests, "get", fail_get)

        html = '<img src="data:image/png;base64,aGVsbG8=">'
        assert rss._inline_remote_images(html) == html

    def test_leaves_non_http_images_untouched(self, monkeypatch):
        def fail_get(*args, **kwargs):
            raise AssertionError("requests.get should not run for a src-less/non-http <img>")

        monkeypatch.setattr(rss.requests, "get", fail_get)

        html = "<p>no images here</p>"
        assert rss._inline_remote_images(html) == html

    def test_a_failing_image_download_leaves_that_image_as_the_original_link(self, monkeypatch):
        """Regression test for the actual production bug this whole function fixes: an image
        that WeasyPrint can't handle used to silently take the *entire story* down with it (see
        _inline_remote_images' docstring). One bad image must not prevent every other image in
        the same body from still being inlined, and must not raise out of this function."""

        def fake_get(url, *, headers, timeout):
            if "broken" in url:
                return _FakeResponse(ok=False, content=b"")
            return _FakeResponse(ok=True, content=_image_bytes("PNG", size=(3, 3)))

        monkeypatch.setattr(rss.requests, "get", fake_get)

        html = (
            '<img src="https://example.com/broken.jpg">'
            '<img src="https://example.com/fine.jpg">'
        )
        result = rss._inline_remote_images(html)

        assert 'src="https://example.com/broken.jpg"' in result
        assert "data:image/jpeg;base64," in result

    def test_a_corrupt_image_body_also_leaves_the_original_link(self, monkeypatch):
        monkeypatch.setattr(
            rss.requests,
            "get",
            lambda *a, **k: _FakeResponse(ok=True, content=b"not actually an image"),
        )

        html = '<img src="https://example.com/corrupt.jpg">'
        result = rss._inline_remote_images(html)

        assert result == html

    def test_get_stories_inlines_images_found_in_the_extracted_article_body(self, monkeypatch):
        """End-to-end: an <img> that readability extracts from a fetched article page ends up
        rewritten to a data: URI in the final Story, exercising get_stories()'s own wiring of
        _inline_remote_images rather than calling it directly."""
        fake_png = _image_bytes("PNG", size=(6, 5))

        class FakeDocument:
            def __init__(self, html):
                pass

            def title(self):
                return "Readable title"

            def summary(self):
                return '<img src="https://example.com/article-photo.jpg">'

        def fake_get(url, *, headers, timeout=None):
            if url == "https://example.com/article-photo.jpg":
                return _FakeResponse(ok=True, content=fake_png)
            return _FakeResponse(ok=True, text="<html></html>")

        monkeypatch.setattr(
            rss.feedparser,
            "parse",
            lambda _: SimpleNamespace(entries=[_feed_entry(summary=None)]),
        )
        monkeypatch.setattr(rss.requests, "get", fake_get)
        monkeypatch.setattr(rss, "Document", FakeDocument)

        provider = rss.RSSFeedStoryProvider("https://example.com/feed.xml")
        stories = provider.get_stories()

        assert "data:image/jpeg;base64," in stories[0].body_html
        assert "https://example.com/article-photo.jpg" not in stories[0].body_html
