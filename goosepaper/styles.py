from __future__ import annotations

import importlib.resources as resources
from dataclasses import dataclass


@dataclass(frozen=True)
class PageProfile:
    name: str
    size: str
    margin_top: str
    margin_right: str
    margin_bottom: str
    margin_left: str
    max_auto_columns: int


_PAGE_PROFILES = {
    "rm1": PageProfile(
        name="rm1",
        size="6.18in 8.24in",
        margin_top="0.34in",
        margin_right="0.24in",
        margin_bottom="0.26in",
        margin_left="0.24in",
        max_auto_columns=2,
    ),
    "remarkable1": PageProfile(
        name="remarkable1",
        size="6.18in 8.24in",
        margin_top="0.34in",
        margin_right="0.24in",
        margin_bottom="0.26in",
        margin_left="0.24in",
        max_auto_columns=2,
    ),
    "remarkable2": PageProfile(
        name="remarkable2",
        size="6.18in 8.24in",
        margin_top="0.34in",
        margin_right="0.24in",
        margin_bottom="0.26in",
        margin_left="0.24in",
        max_auto_columns=2,
    ),
    "paper_pro": PageProfile(
        name="paper_pro",
        size="7.08in 9.44in",
        margin_top="0.36in",
        margin_right="0.26in",
        margin_bottom="0.28in",
        margin_left="0.26in",
        max_auto_columns=2,
    ),
    "paper_pro_move": PageProfile(
        name="paper_pro_move",
        size="3.58in 6.36in",
        margin_top="0.22in",
        margin_right="0.16in",
        margin_bottom="0.20in",
        margin_left="0.16in",
        max_auto_columns=1,
    ),
    "letter": PageProfile(
        name="letter",
        size="8.5in 11in",
        margin_top="0.52in",
        margin_right="0.34in",
        margin_bottom="0.38in",
        margin_left="0.34in",
        max_auto_columns=2,
    ),
    "a4": PageProfile(
        name="a4",
        size="210mm 297mm",
        margin_top="13mm",
        margin_right="9mm",
        margin_bottom="10mm",
        margin_left="9mm",
        max_auto_columns=2,
    ),
}


PAGE_PROFILE_CHOICES = tuple(_PAGE_PROFILES)

_THEME_FONTS = {
    "Academy": {
        "body": 'Georgia, "Times New Roman", serif',
        "display": '"Times New Roman", Georgia, serif',
        "sans": '"Times New Roman", Georgia, serif',
    },
    "Autumn": {
        "body": 'Georgia, "Times New Roman", serif',
        "display": '"Playfair Display", Georgia, serif',
        "sans": '"Oswald", "Helvetica Neue", sans-serif',
    },
    "FifthAvenue": {
        "body": '"Open Sans", "Helvetica Neue", sans-serif',
        "display": '"Source Serif Pro", Georgia, serif',
        "sans": '"Open Sans", "Helvetica Neue", sans-serif',
    },
    "GrayMaiden": {
        "body": '"Source Serif 4", Georgia, serif',
        "display": '"Newsreader", Georgia, serif',
        "sans": '"Libre Franklin", "Helvetica Neue", sans-serif',
    },
}

_THEME_AUTO_COLUMNS = {
    "Academy": 1,
    "FifthAvenue": 2,
    "Autumn": 2,
    "GrayMaiden": 2,
}


def read_stylesheets(path) -> list[str]:
    if path.is_file():
        return path.read_text().strip("\n").split("\n")
    return []


def read_css(path):
    return path.read_text()


class Style:
    def __init__(self, style: str = ""):
        self.style_name = style or "FifthAvenue"
        if not self.read_style(self.style_name):
            if style:
                print(f"Oops! {style} style not found or broken. Use default style.")
            self.style_name = "FifthAvenue"
            self.read_style(self.style_name)

    def get_stylesheets(self) -> list[str]:
        return list(getattr(self, "_stylesheets", []))

    def get_page_profile(self, page_profile: str = "remarkable2") -> PageProfile:
        profile_name = page_profile or "remarkable2"
        if profile_name not in _PAGE_PROFILES:
            print(
                f"Oops! {profile_name} page profile not found or broken. Use default page profile."
            )
            profile_name = "remarkable2"
        return _PAGE_PROFILES[profile_name]

    def get_css(
        self,
        font_size: int = 14,
        body_font: str | None = None,
        layout: str = "auto",
        page_profile: str = "remarkable2",
    ) -> str:
        profile = self.get_page_profile(page_profile)
        effective_columns = self.resolve_column_count(layout, page_profile)
        css_parts = [
            _base_print_css(profile, font_size, effective_columns),
            getattr(self, "_css", ""),
        ]
        if body_font:
            css_parts.append(_body_font_override_css(body_font))
        return "\n".join(css_parts)

    def get_epub_css(self, font_size: int = 14, body_font: str | None = None) -> str:
        theme_fonts = _THEME_FONTS.get(self.style_name, _THEME_FONTS["FifthAvenue"])
        body_stack = _font_stack(body_font, theme_fonts["body"])
        return f"""
        body {{
            font-family: {body_stack};
            font-size: {float(font_size):.2f}pt;
            line-height: 1.42;
        }}

        .story-headline,
        h1, h2, h3 {{
            font-family: {theme_fonts["display"]};
        }}

        .byline {{
            font-family: {theme_fonts["sans"]};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        """

    def read_style(self, style: str) -> bool:
        for root in _style_roots():
            css, stylesheets = _read_style_from_root(root, style)
            if css is not None:
                self._stylesheets = stylesheets
                self._css = css
                return True
        return False

    def resolve_column_count(
        self, layout: str = "auto", page_profile: str = "remarkable2"
    ) -> int:
        profile = self.get_page_profile(page_profile)
        if layout == "auto":
            default_columns = _THEME_AUTO_COLUMNS.get(self.style_name, 2)
            return max(1, min(default_columns, profile.max_auto_columns))
        return {"1col": 1, "2col": 2, "3col": 3}.get(layout, profile.max_auto_columns)


def _style_roots():
    yield resources.files("goosepaper").joinpath("assets", "styles")


def _read_style_from_root(root, style):
    path = root.joinpath(style)
    if path.is_dir():
        css_file = next(
            (entry for entry in path.iterdir() if entry.name.endswith(".css")),
            None,
        )
        if css_file is None:
            return None, []
        return read_css(css_file), read_stylesheets(path.joinpath("stylesheets.txt"))

    css_path = root.joinpath(f"{style}.css")
    if css_path.is_file():
        return read_css(css_path), []

    return None, []


def _base_print_css(
    profile: PageProfile, font_size: int, effective_columns: int
) -> str:
    toc_columns = 1 if effective_columns == 1 else 2
    return f"""
    @page {{
        size: {profile.size};
        margin-top: {profile.margin_top};
        margin-right: {profile.margin_right};
        margin-bottom: {profile.margin_bottom};
        margin-left: {profile.margin_left};
    }}

    * {{
        box-sizing: border-box;
    }}

    html {{
        color: #111;
    }}

    body {{
        margin: 0;
        color: #111;
        font-size: {int(font_size)}pt;
        line-height: 1.45;
    }}

    a {{
        color: inherit;
    }}

    p,
    ul,
    ol,
    blockquote,
    figure {{
        margin-top: 0.45rem;
        margin-bottom: 0.75rem;
    }}

    ul,
    ol {{
        padding-left: 1.2rem;
    }}

    li {{
        margin-bottom: 0.18rem;
    }}

    img {{
        max-width: 100%;
        height: auto;
    }}

    .header {{
        position: relative;
        margin: 0 0 0.65rem;
        padding: 0 0 0.55rem;
        border-bottom: 1.5pt solid #111;
    }}

    body.has-toc .header {{
        margin-bottom: 0.35rem;
    }}

    .header::after,
    .stories::after {{
        content: "";
        display: block;
        clear: both;
    }}

    .header .ear {{
        width: 24%;
        font-size: 0.76em;
    }}

    .header .left-ear {{
        float: left;
        margin: 0.25rem 1rem 0 0;
    }}

    .header .right-ear {{
        float: right;
        margin: 0.25rem 0 0 1rem;
    }}

    .header .ear:empty,
    .sidebar:empty {{
        display: none;
    }}

    .header.has-left-ear .masthead {{
        margin-left: 26%;
    }}

    .header.has-right-ear .masthead {{
        margin-right: 26%;
    }}

    .header.has-left-ear.has-right-ear .masthead {{
        margin-left: 20%;
        margin-right: 20%;
    }}

    .masthead {{
        min-height: 3.5rem;
    }}

    .masthead h1 {{
        margin: 0;
        line-height: 0.95;
    }}

    .edition-line {{
        margin: 0.3rem 0 0;
        font-size: 0.86em;
        line-height: 1.25;
    }}

    .table-of-contents {{
        margin: 0 0 0.85rem;
        padding: 0.15rem 0 0.45rem;
        border-bottom: 0.9pt solid #d2d2d2;
    }}

    .table-of-contents__label {{
        margin: 0 0 0.35rem;
        font-size: 0.7em;
        letter-spacing: 0.18em;
        text-transform: uppercase;
    }}

    .table-of-contents__entries {{
        margin: 0;
        column-count: {toc_columns};
        column-gap: 1.4rem;
    }}

    .table-of-contents__entry {{
        break-inside: avoid;
        margin-bottom: 0.3rem;
    }}

    .table-of-contents__link {{
        display: block;
        text-decoration: none;
    }}

    .table-of-contents__link::after {{
        content: leader(dotted) target-counter(attr(href), page);
    }}

    .stories {{
        width: 100%;
    }}

    .main-stories,
    .sidebar {{
        width: 100%;
    }}

    .main-stories {{
        column-gap: 1.35rem;
        column-fill: balance;
    }}

    .stories--1col .main-stories {{
        column-count: 1;
    }}

    .stories--2col:not(.has-sidebar) .main-stories {{
        column-count: 2;
    }}

    .stories--3col:not(.has-sidebar) .main-stories {{
        column-count: 3;
        column-gap: 1rem;
    }}

    .stories--2col.has-sidebar .main-stories {{
        width: 100%;
        column-count: 2;
    }}

    .stories--2col.has-sidebar .sidebar {{
        display: block;
        width: 100%;
        margin-top: 0.85rem;
        padding-top: 0.7rem;
        border-top: 0.9pt solid #d2d2d2;
        column-count: 2;
        column-gap: 1.2rem;
    }}

    .stories--3col.has-sidebar .main-stories {{
        width: 100%;
        column-count: 3;
    }}

    .stories--3col.has-sidebar .sidebar {{
        display: block;
        width: 100%;
        margin-top: 0.85rem;
        padding-top: 0.7rem;
        border-top: 0.9pt solid #d2d2d2;
        column-count: 2;
        column-gap: 1.2rem;
    }}

    .stories--1col.has-sidebar .sidebar {{
        display: block;
        margin-top: 1rem;
        padding-top: 0.75rem;
        border-top: 0.9pt solid #d2d2d2;
    }}

    .sidebar-title {{
        margin: 0 0 0.6rem;
        font-size: 0.72em;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }}

    .story-section-heading {{
        break-after: avoid;
        margin: 0 0 0.55rem;
        padding-top: 0.08rem;
    }}

    .story-section-title {{
        margin: 0;
        font-size: 0.72em;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }}

    article {{
        margin: 0;
        text-align: left;
    }}

    .main-stories > article,
    .sidebar > article {{
        margin-bottom: 1rem;
        padding-bottom: 0.9rem;
        border-bottom: 0.9pt solid #d9d9d9;
    }}

    .main-stories > article:last-child,
    .sidebar > article:last-child {{
        margin-bottom: 0;
        padding-bottom: 0;
        border-bottom: 0;
    }}

    article > h1,
    article > h2,
    article > h3 {{
        margin-top: 0;
        break-after: avoid;
    }}

    article > .byline {{
        margin: 0 0 0.55rem;
        font-size: 0.75em;
    }}

    article.story-short > .story-headline {{
        font-size: 1.16em;
        line-height: 1.12;
        margin-bottom: 0.28rem;
    }}

    .sidebar article.story-short > .story-headline {{
        font-size: 0.96em;
    }}

    .story-body > :first-child {{
        margin-top: 0;
    }}

    .story-body > :last-child {{
        margin-bottom: 0;
    }}

    .ear article {{
        margin: 0;
        padding: 0.75rem 0.85rem;
    }}

    .ear article h1 {{
        margin-bottom: 0.2rem;
    }}

    .ear .byline {{
        display: none;
    }}

    .ear .story-body {{
        text-align: center;
    }}

    .ear .story-body p {{
        margin: 0.2rem 0;
    }}

    .ear .story-body p:first-child {{
        font-size: 1.15em;
    }}
    """


def _body_font_override_css(body_font: str) -> str:
    return f"""
    body,
    article,
    .stories,
    .story-body {{
        font-family: {_font_stack(body_font)} !important;
    }}
    """


def _font_stack(override: str | None, fallback: str = "serif") -> str:
    if not override:
        return fallback
    cleaned = override.strip()
    if not cleaned:
        return fallback
    if "," in cleaned:
        return cleaned
    if cleaned.startswith('"') or cleaned.startswith("'"):
        return f"{cleaned}, serif"
    return f'"{cleaned}", serif'
