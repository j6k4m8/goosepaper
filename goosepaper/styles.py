import pathlib


def read_stylesheets(path: pathlib.Path) -> list:
    if path.is_file():
        return path.read_text().strip("\n").split("\n")
    else:
        return []


def read_css(path: pathlib.Path):
    return path.read_text()


class Style:
    def __init__(self, style=""):
        if style:
            try:
                self.read_style(style)
            except (FileNotFoundError, StopIteration):
                print(f"Oops! {style} style not found or broken. Use default style.")
        self.read_default_style()  # if style not found
        return

    def get_stylesheets(self) -> list:
        return getattr(self, "_stylesheets", [])

    def get_css(self, font_size: int = None):
        font_size = str(font_size)
        if font_size:
            self._css += f"""
        .stories {{
            font-size: {font_size}pt !important;
        }}
        article>.byline {{
            font-size: {font_size}pt !important;
        }}
        """
        return getattr(self, "_css", "")

    def read_style(self, style):
        path = pathlib.Path("./styles/") / style
        if path.is_dir():
            if not hasattr(self, "_css"):
                self._stylesheets = read_stylesheets(path / "stylesheets.txt")
                self._css = read_css(next(path.glob("*.css")))
        elif path.with_suffix(".css").is_file():
            self._stylesheets = []
            self._css = read_css(path.with_suffix(".css"))

    def read_default_style(self):  # code copied from FifthAvenueStyle
        if not hasattr(self, "_css"):
            self._stylesheets = [
                "https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,400;0,700;1,400;1,700&family=Source+Serif+Pro:ital,wght@0,400;0,700;1,400&display=swap"
            ]
            self._css = """
                @page {
                    margin-top: 0.5in;
                    margin-right: 0.2in;
                    margin-left: 0.65in;
                    margin-bottom: 0.2in;
                }

                body {
                    font-family: "Open Sans";
                }

                .header {
                    padding: 1em;
                    height: 10em;
                }

                .header div {
                    float: left;
                    display: block;
                }

                .header .ear {
                    float: right;
                }

                ul, li, ol {
                    margin-left: 0; padding-left: 0.15em;
                }

                .stories {
                    font-size: 14pt;
                }

                .ear article {
                    border: 1px groove black;
                    padding: 1em;
                    margin: 1em;
                    font-size: 11pt;
                }
                .ear article h1 {
                    font-family: "Source Serif Pro";
                    font-size: 10pt;
                    font-weight: normal;
                }

                article {
                    text-align: justify;
                    line-height: 1.3em;
                }

                .longform {
                    page-break-after: always;
                }

                article>h1 {
                    font-family: "Source Serif Pro";
                    font-weight: 400;
                    font-size: 23pt;
                    text-indent: 0;
                    margin-bottom: 0.25em;
                    line-height: 1.2em;
                    text-align: left;
                }
                article>h1.priority-low {
                    font-family: "Open Sans";
                    font-size: 18pt;
                    font-weight: 400;
                    text-indent: 0;
                    border-bottom: 1px solid #dedede;
                    margin-bottom: 0.15em;
                }

                article>.byline {
                    font-family: "Open Sans";
                    font-size: 14pt;
                    font-weight: 400;
                    text-indent: 0;
                    border-bottom: 1px solid #dedede;
                    margin-top: 1.33em;
                    margin-bottom: 1.33em;
                    margin-left: 0;
                    margin-right: 0;
                }

                article>h3 {
                    font-family: "Open Sans";
                    font-weight: 400;
                    font-size: 18pt;
                    text-indent: 0;
                }

                section>h1,
                section>h2,
                section>h3,
                section>h4,
                section>h5 {
                    border-left: 5px solid #dedede;
                    padding-left: 1em;
                }

                figure {
                    border: 1px solid black;
                    text-indent: 0;
                    width: auto;
                }

                .stories article.story img {
                    width: 100%;
                }

                figure>span {
                    font-size: 0;
                }

                .row {
                    column-count: 2;
                }"""
